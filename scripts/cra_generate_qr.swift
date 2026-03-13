import AppKit
import CoreImage
import Foundation

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
let representation = NSCIImageRep(ciImage: scaledImage)
let image = NSImage(size: representation.size)
image.addRepresentation(representation)

guard let tiffData = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let pngData = bitmap.representation(using: NSBitmapImageRep.FileType.png, properties: [:]) else {
    fputs("failed to render PNG data for QR image\n", stderr)
    exit(1)
}

let outputURL = URL(fileURLWithPath: outputPath)

do {
    try pngData.write(to: outputURL)
    print(outputPath)
} catch {
    fputs("failed to write QR image: \(error)\n", stderr)
    exit(1)
}
