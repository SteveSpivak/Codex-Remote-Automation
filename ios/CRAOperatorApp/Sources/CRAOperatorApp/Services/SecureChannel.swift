import CryptoKit
import Foundation

enum SecureChannelError: Error {
    case invalidSecret
    case invalidTag
    case invalidUTF8
}

struct SecureSessionState {
    let sessionId: String
    let phoneDeviceId: String
    let sessionSecret: Data
    let keyEpoch: Int
    var nextOutboundCounter: Int
    var lastInboundCounter: Int
    var lastAppliedBridgeOutboundSeq: Int
}

struct SecureChannel {
    static func randomBase64(byteCount: Int = 32) -> String {
        Data((0..<byteCount).map { _ in UInt8.random(in: .min ... .max) }).base64EncodedString()
    }

    static func decodeBase64(_ value: String) throws -> Data {
        guard let decoded = Data(base64Encoded: value) else {
            throw SecureChannelError.invalidSecret
        }
        return decoded
    }

    static func deriveBytes(secret: String, parts: [String], length: Int = 32) throws -> Data {
        let keyData = try decodeBase64(secret)
        let key = SymmetricKey(data: keyData)
        var output = Data()
        var counter: UInt32 = 1
        while output.count < length {
            var data = Data("cra-bridge-v1|".utf8)
            for part in parts {
                let partData = Data(part.utf8)
                var count = UInt16(partData.count).bigEndian
                data.append(Data(bytes: &count, count: MemoryLayout<UInt16>.size))
                data.append(partData)
            }
            var beCounter = counter.bigEndian
            data.append(Data(bytes: &beCounter, count: MemoryLayout<UInt32>.size))
            let mac = HMAC<SHA256>.authenticationCode(for: data, using: key)
            output.append(contentsOf: mac)
            counter += 1
        }
        return output.prefix(length)
    }

    static func computeTag(secret: String, aad: Data, ciphertext: Data) throws -> String {
        let key = SymmetricKey(data: try decodeBase64(secret))
        var data = Data("tag|".utf8)
        data.append(aad)
        data.append(ciphertext)
        let tag = HMAC<SHA256>.authenticationCode(for: data, using: key)
        return Data(tag).base64EncodedString()
    }

    static func encrypt(secret: String, aad: Data, plaintext: String) throws -> (ciphertext: String, tag: String) {
        let raw = Data(plaintext.utf8)
        let keystream = try deriveBytes(secret: secret, parts: ["stream", aad.base64EncodedString()], length: raw.count)
        let ciphertext = Data(zip(raw, keystream).map(^))
        let tag = try computeTag(secret: secret, aad: aad, ciphertext: ciphertext)
        return (ciphertext.base64EncodedString(), tag)
    }

    static func decrypt(secret: String, aad: Data, ciphertext: String, tag: String) throws -> String {
        let ciphertextData = try decodeBase64(ciphertext)
        let expectedTag = try computeTag(secret: secret, aad: aad, ciphertext: ciphertextData)
        guard expectedTag == tag else {
            throw SecureChannelError.invalidTag
        }
        let keystream = try deriveBytes(secret: secret, parts: ["stream", aad.base64EncodedString()], length: ciphertextData.count)
        let plaintext = Data(zip(ciphertextData, keystream).map(^))
        guard let decoded = String(data: plaintext, encoding: .utf8) else {
            throw SecureChannelError.invalidUTF8
        }
        return decoded
    }

    static func handshakeAAD(sessionId: String, handshakeMode: String, phoneDeviceId: String, clientNonce: String) -> Data {
        let payload = [
            "sessionId": sessionId,
            "handshakeMode": handshakeMode,
            "phoneDeviceId": phoneDeviceId,
            "clientNonce": clientNonce
        ]
        return Data(try! JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]))
    }

    static func authAAD(
        sessionId: String,
        phoneDeviceId: String,
        clientNonce: String,
        serverNonce: String,
        keyEpoch: Int
    ) -> Data {
        let payload: [String: Any] = [
            "sessionId": sessionId,
            "phoneDeviceId": phoneDeviceId,
            "clientNonce": clientNonce,
            "serverNonce": serverNonce,
            "keyEpoch": keyEpoch
        ]
        return Data(try! JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]))
    }

    static func envelopeAAD(sessionId: String, keyEpoch: Int, sender: String, counter: Int) -> Data {
        let payload: [String: Any] = [
            "sessionId": sessionId,
            "keyEpoch": keyEpoch,
            "sender": sender,
            "counter": counter
        ]
        return Data(try! JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]))
    }
}
