import SwiftUI

struct PairingView: View {
    @ObservedObject var store: ApprovalStore

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("CRA Pairing")
                .font(.largeTitle.bold())
            Text("Paste the CRA bridge pairing payload or scan it into this app.")
                .foregroundStyle(.secondary)

            TextEditor(text: $store.pairingText)
                .frame(minHeight: 220)
                .font(.system(.body, design: .monospaced))
                .padding(8)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.secondary.opacity(0.2)))

            Button("Connect to CRA Bridge") {
                Task {
                    try? await store.connectFromPairingText()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(24)
    }
}
