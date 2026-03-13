import SwiftUI

@main
struct CRAOperatorApp: App {
    @StateObject private var store = ApprovalStore()

    var body: some Scene {
        WindowGroup {
            RootView(store: store)
        }
    }
}
