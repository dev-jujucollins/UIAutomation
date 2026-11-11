import Foundation
import Network

/// Serves a folder of test pages on 127.0.0.1 from inside the test runner.
///
/// Simulators share the Mac's network, so Safari on the simulator reaches this server;
/// a physical device does not. Replaces src/uiautomation/utils/local_site.py.
final class FixtureSite {
    enum SiteError: Error { case missingFolder, notListening }

    let baseURL: URL
    private let listener: NWListener
    private let queue = DispatchQueue(label: "uiautomation.fixture-site")

    /// Serve the "site" folder bundled with the tests (tests/integration/fixtures/site).
    static func bundled() throws -> FixtureSite {
        guard let root = Bundle(for: FixtureSite.self).url(forResource: "site", withExtension: nil)
        else { throw SiteError.missingFolder }
        return try FixtureSite(root: root)
    }

    init(root: URL) throws {
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        listener = try NWListener(using: parameters)

        let ready = DispatchSemaphore(value: 0)
        listener.stateUpdateHandler = { state in
            switch state {
            case .ready, .failed, .cancelled: ready.signal()
            default: break
            }
        }
        let queue = self.queue
        listener.newConnectionHandler = { connection in
            FixtureSite.serve(connection, root: root, on: queue)
        }
        listener.start(queue: queue)
        guard ready.wait(timeout: .now() + 5) == .success, let port = listener.port else {
            listener.cancel()
            throw SiteError.notListening
        }
        baseURL = URL(string: "http://127.0.0.1:\(port.rawValue)/")!
    }

    func stop() {
        listener.cancel()
    }

    private static func serve(_ connection: NWConnection, root: URL, on queue: DispatchQueue) {
        connection.start(queue: queue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { data, _, _, _ in
            let request = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
            // "GET /second.html?x=1 HTTP/1.1" -> "second.html"
            let target = request.split(separator: " ").dropFirst().first.map(String.init) ?? "/"
            var name = String((target.split(separator: "?").first ?? "/").dropFirst())
            if name.isEmpty { name = "index.html" }

            var status = "404 Not Found"
            var body = Data("Not found".utf8)
            if !name.contains(".."),
               let file = try? Data(contentsOf: root.appendingPathComponent(name))
            {
                status = "200 OK"
                body = file
            }
            let header =
                "HTTP/1.1 \(status)\r\nContent-Type: text/html; charset=utf-8\r\n"
                + "Content-Length: \(body.count)\r\nConnection: close\r\n\r\n"
            connection.send(
                content: Data(header.utf8) + body,
                completion: .contentProcessed { _ in connection.cancel() })
        }
    }
}
