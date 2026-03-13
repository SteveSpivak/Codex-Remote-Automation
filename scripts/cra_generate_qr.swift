import CoreImage
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let arguments = CommandLine.arguments

guard arguments.count == 3 else {
    fputs("usage: cra_generate_qr.swift <content> <output-path>\n", stderr)
    exit(2)
}

let content = arguments[1]
let outputPath = arguments[2]

guard let data = content.data(using: .utf8) else {
    fputs("could not encode QR content as UTF-8\n", stderr)
    exit(1)
}

guard let filter = CIFilter(name: "CIQRCodeGenerator") else {
    fputs("CIQRCodeGenerator is unavailable\n", stderr)
    exit(1)
}

filter.setValue(data, forKey: "inputMessage")
filter.setValue("M", forKey: "inputCorrectionLevel")

guard let outputImage = filter.outputImage else {
    fputs("qr filter did not produce an image\n", stderr)
    exit(1)
}

let scaledImage = outputImage.transformed(by: CGAffineTransform(scaleX: 12, y: 12))
let context = CIContext(options: nil)
let outputRect = scaledImage.extent.integral

guard let cgImage = context.createCGImage(scaledImage, from: outputRect) else {
    fputs("failed to create CGImage for QR image\n", stderr)
    exit(1)
}

let outputURL = URL(fileURLWithPath: outputPath)

do {
    guard let destination = CGImageDestinationCreateWithURL(
        outputURL as CFURL,
        UTType.png.identifier as CFString,
        1,
        nil
    ) else {
        fputs("failed to create PNG destination\n", stderr)
        exit(1)
    }

    CGImageDestinationAddImage(destination, cgImage, nil)
    if !CGImageDestinationFinalize(destination) {
        fputs("failed to finalize PNG destination\n", stderr)
        exit(1)
    }

    print(outputPath)
} catch {
    fputs("failed to write QR image: \(error)\n", stderr)
    exit(1)
}
