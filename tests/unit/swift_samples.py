"""xcresulttool output in the shape Xcode 27.2 produces, trimmed to what the code reads."""

SUMMARY = {
    "devicesAndConfigurations": [
        {
            "device": {
                "deviceName": "iPhone 18 Pro",
                "modelName": "iPhone 18 Pro",
                "osVersion": "27.2",
                "platform": "iOS Simulator",
            }
        }
    ],
    "startTime": 1794351919.958,
    "finishTime": 1794352060.633,
    "result": "Failed",
}

TESTS = {
    "testNodes": [
        {
            "nodeType": "Test Plan",
            "name": "All",
            "children": [
                {
                    "nodeType": "UI test bundle",
                    "name": "UIAutomationUITests",
                    "children": [
                        {
                            "nodeType": "Test Suite",
                            "name": "ContactsTests",
                            "children": [
                                {
                                    "nodeType": "Test Case",
                                    "name": "testContactCreateReopenEditDelete()",
                                    "result": "Skipped",
                                    "durationInSeconds": 7.3,
                                    "children": [
                                        {
                                            "nodeType": "Skip Message",
                                            "name": "Test skipped - Owned-data tests require "
                                            "UIAUTOMATION_RUN_LIFECYCLE=1",
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "nodeType": "Test Suite",
                            "name": "SettingsTests",
                            "children": [
                                {
                                    "nodeType": "Test Case",
                                    "name": "testNavigateToGeneral()",
                                    "result": "Failed",
                                    "durationInSeconds": 11.2,
                                    "children": [
                                        {
                                            "nodeType": "Failure Message",
                                            "name": "XCTAssertTrue failed - <b>General</b> missing",
                                            "sourceLocation": {
                                                "filePath": "/repo/swift/Settings/SettingsTests.swift",
                                                "lineNumber": 30,
                                            },
                                        }
                                    ],
                                },
                                {
                                    "nodeType": "Test Case",
                                    "name": "testSettingsAppLaunches()",
                                    "result": "Passed",
                                    "durationInSeconds": 9.3,
                                },
                            ],
                        },
                    ],
                }
            ],
        }
    ]
}
