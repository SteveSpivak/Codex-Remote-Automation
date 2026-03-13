import SwiftUI

struct RootView: View {
    @ObservedObject var store: ApprovalStore

    var body: some View {
        if store.relayClient.snapshot == nil {
            PairingView(store: store)
        } else {
            ApprovalListView(store: store)
        }
    }
}
