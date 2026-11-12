#!/bin/bash
# Run the Swift XCUITest suite on a simulator.
#
#   ./run-tests.sh                              every test that needs no opt-in
#   ./run-tests.sh RemindersTests               one test class
#   ./run-tests.sh MessagesTests/testMessagesHomeIsReady
#   ./run-tests.sh --plan Smoke                 a test plan (All, Smoke, Journey)
#   ./run-tests.sh --lifecycle ContactsTests    include tests that save and delete data
#   ./run-tests.sh --plan Smoke --email-preview write run.json, report.html and the email
#   ./run-tests.sh --plan Smoke --email         ...and send it (see ../docs/reporting.md)
#
# Options:
#   --device NAME        simulator name (default: iPhone 18 Pro)
#   --os VERSION         iOS version (default: 27.2)
#   --udid UDID          exact simulator, instead of --device/--os
#   --plan NAME          run a test plan instead of every test
#   --lifecycle          enable owned-data lifecycle tests (use a disposable simulator)
#   --maps-navigation    enable the Maps turn-by-turn guidance test
#   --diagnostics        enable locator-health and accessibility-label diagnostics
#   --result-bundle PATH save the .xcresult bundle here (PATH must not exist yet)
#   --email, --email-preview, --email-config FILE, --artifacts-dir DIR
#                        hand the run to "uiautomation swift", which records it under
#                        ../artifacts, builds report.html, and emails or previews it
#   --                   pass the remaining arguments to xcodebuild unchanged
set -euo pipefail
cd "$(dirname "$0")"

# Reporting lives in the Python CLI, which calls back into this script for the run itself.
for argument in "$@"; do
  case "$argument" in
    --) break ;;
    --email|--email-preview)
      cd ..
      exec uv run uiautomation swift "$@" ;;
  esac
done

device="iPhone 18 Pro"
os="27.2"
udid=""
plan=""
bundle=""
selectors=()
extra=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) device="$2"; shift 2 ;;
    --os) os="$2"; shift 2 ;;
    --udid) udid="$2"; shift 2 ;;
    --plan) plan="$2"; shift 2 ;;
    --result-bundle) bundle="$2"; shift 2 ;;
    --lifecycle) export TEST_RUNNER_UIAUTOMATION_RUN_LIFECYCLE=1; shift ;;
    --maps-navigation) export TEST_RUNNER_UIAUTOMATION_RUN_MAPS_NAVIGATION=1; shift ;;
    --diagnostics) export TEST_RUNNER_UIAUTOMATION_RUN_DIAGNOSTICS=1; shift ;;
    --) shift; extra=("$@"); break ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *) selectors+=("-only-testing:UIAutomationUITests/$1"); shift ;;
  esac
done

if [[ -n "$udid" ]]; then
  destination="platform=iOS Simulator,id=$udid"
else
  destination="platform=iOS Simulator,name=$device,OS=$os"
fi

args=(test -project UIAutomationSwift.xcodeproj -scheme UIAutomationUITests
      -destination "$destination")
[[ -n "$plan" ]] && args+=(-testPlan "$plan")
[[ -n "$bundle" ]] && args+=(-resultBundlePath "$bundle")

exec xcodebuild "${args[@]}" ${selectors[@]+"${selectors[@]}"} ${extra[@]+"${extra[@]}"}
