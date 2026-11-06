// Prints the text Vision reads in a screenshot, one line per region. macOS only.
// Used by scripts/live_ui_check.py to read the iOS simulator screen.
import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 2, let image = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("usage: ocr_text IMAGE\n".data(using: .utf8)!)
    exit(64)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
try VNImageRequestHandler(cgImage: cgImage).perform([request])
for observation in request.results ?? [] {
    if let text = observation.topCandidates(1).first?.string { print(text) }
}
