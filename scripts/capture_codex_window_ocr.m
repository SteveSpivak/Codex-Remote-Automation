#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <Vision/Vision.h>

static NSDictionary *rect_payload(CGRect rect) {
    return @{
        @"x": @(rect.origin.x),
        @"y": @(rect.origin.y),
        @"width": @(rect.size.width),
        @"height": @(rect.size.height),
    };
}

static void print_json(NSDictionary *payload) {
    NSError *error = nil;
    NSData *data = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted | NSJSONWritingSortedKeys error:&error];
    if (!data) {
        fprintf(stderr, "%s\n", error.localizedDescription.UTF8String);
        return;
    }
    NSString *text = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    printf("%s\n", text.UTF8String);
}

static CGRect rect_from_window_entry(NSDictionary *entry) {
    NSDictionary *bounds = entry[(NSString *)kCGWindowBounds];
    if (![bounds isKindOfClass:[NSDictionary class]]) {
        return CGRectZero;
    }
    return CGRectMake(
        [bounds[@"X"] doubleValue],
        [bounds[@"Y"] doubleValue],
        [bounds[@"Width"] doubleValue],
        [bounds[@"Height"] doubleValue]
    );
}

static NSDictionary *error_payload(NSString *note, NSString *imageOutput) {
    return @{
        @"status": @"error",
        @"window": [NSNull null],
        @"text_items": @[],
        @"image_output": imageOutput ?: [NSNull null],
        @"note": note ?: @"Unknown error.",
    };
}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *appName = @"Codex";
        NSNumber *pid = nil;
        NSString *imageOutput = nil;

        for (int i = 1; i < argc; i += 1) {
            NSString *argument = [NSString stringWithUTF8String:argv[i]];
            if ([argument isEqualToString:@"--app-name"] && i + 1 < argc) {
                appName = [NSString stringWithUTF8String:argv[++i]];
            } else if ([argument isEqualToString:@"--pid"] && i + 1 < argc) {
                pid = @((int)[[NSString stringWithUTF8String:argv[++i]] intValue]);
            } else if ([argument isEqualToString:@"--image-output"] && i + 1 < argc) {
                imageOutput = [NSString stringWithUTF8String:argv[++i]];
            }
        }

        NSArray *windows = CFBridgingRelease(
            CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements, kCGNullWindowID)
        );

        NSDictionary *matchedWindow = nil;
        CGRect matchedBounds = CGRectZero;
        NSNumber *windowID = nil;
        for (NSDictionary *entry in windows) {
            NSString *ownerName = entry[(NSString *)kCGWindowOwnerName] ?: @"";
            NSNumber *ownerPid = entry[(NSString *)kCGWindowOwnerPID];
            NSNumber *layer = entry[(NSString *)kCGWindowLayer] ?: @0;
            CGRect bounds = rect_from_window_entry(entry);

            if (layer.integerValue != 0 || bounds.size.width < 40 || bounds.size.height < 40) {
                continue;
            }
            if (pid != nil && ownerPid.intValue != pid.intValue) {
                continue;
            }
            if (pid == nil && ![ownerName isEqualToString:appName]) {
                continue;
            }

            NSNumber *candidateWindowID = entry[(NSString *)kCGWindowNumber];
            if (candidateWindowID == nil) {
                continue;
            }

            matchedWindow = entry;
            matchedBounds = bounds;
            windowID = candidateWindowID;
            break;
        }

        if (matchedWindow == nil || windowID == nil) {
            print_json(error_payload(@"No matching on-screen window was found.", imageOutput));
            return 1;
        }

        NSString *capturePath = imageOutput;
        BOOL shouldDeleteCapture = NO;
        if (capturePath == nil) {
            capturePath = [NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"cra-window-%@.png", NSUUID.UUID.UUIDString]];
            shouldDeleteCapture = YES;
        }

        NSTask *captureTask = [[NSTask alloc] init];
        captureTask.launchPath = @"/usr/sbin/screencapture";
        captureTask.arguments = @[
            @"-x",
            [NSString stringWithFormat:@"-R%.0f,%.0f,%.0f,%.0f", matchedBounds.origin.x, matchedBounds.origin.y, matchedBounds.size.width, matchedBounds.size.height],
            capturePath,
        ];
        [captureTask launch];
        [captureTask waitUntilExit];
        if (captureTask.terminationStatus != 0) {
            print_json(error_payload(@"Failed to capture the target window. Screen Recording permission may be required.", imageOutput));
            return 2;
        }

        NSURL *captureURL = [NSURL fileURLWithPath:capturePath];
        CGImageSourceRef imageSource = CGImageSourceCreateWithURL((__bridge CFURLRef)captureURL, NULL);
        CGImageRef imageRef = imageSource != nil ? CGImageSourceCreateImageAtIndex(imageSource, 0, NULL) : nil;
        if (imageRef == nil) {
            if (imageSource != nil) {
                CFRelease(imageSource);
            }
            if (shouldDeleteCapture) {
                [[NSFileManager defaultManager] removeItemAtPath:capturePath error:nil];
            }
            print_json(error_payload(@"Failed to open the captured window image.", imageOutput));
            return 3;
        }

        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.usesLanguageCorrection = NO;

        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:imageRef options:@{}];
        NSError *visionError = nil;
        BOOL didRecognize = [handler performRequests:@[request] error:&visionError];
        if (!didRecognize) {
            NSDictionary *payload = error_payload(visionError.localizedDescription, imageOutput);
            print_json(payload);
            CGImageRelease(imageRef);
            CFRelease(imageSource);
            if (shouldDeleteCapture) {
                [[NSFileManager defaultManager] removeItemAtPath:capturePath error:nil];
            }
            return 4;
        }

        NSMutableArray *textItems = [NSMutableArray array];
        for (VNRecognizedTextObservation *observation in request.results ?: @[]) {
            VNRecognizedText *candidate = [[observation topCandidates:1] firstObject];
            if (candidate == nil) {
                continue;
            }

            CGRect box = observation.boundingBox;
            double width = box.size.width * matchedBounds.size.width;
            double height = box.size.height * matchedBounds.size.height;
            double x = matchedBounds.origin.x + (box.origin.x * matchedBounds.size.width);
            double y = matchedBounds.origin.y + ((1.0 - box.origin.y - box.size.height) * matchedBounds.size.height);

            [textItems addObject:@{
                @"text": candidate.string ?: @"",
                @"confidence": @(candidate.confidence),
                @"screen_center": @{
                    @"x": @(x + (width / 2.0)),
                    @"y": @(y + (height / 2.0)),
                },
                @"bounds": @{
                    @"x": @(x),
                    @"y": @(y),
                    @"width": @(width),
                    @"height": @(height),
                },
            }];
        }

        NSDictionary *payload = @{
            @"status": @"ok",
            @"window": @{
                @"id": windowID,
                @"owner_name": matchedWindow[(NSString *)kCGWindowOwnerName] ?: @"",
                @"name": matchedWindow[(NSString *)kCGWindowName] ?: @"",
                @"bounds": rect_payload(matchedBounds),
            },
            @"text_items": textItems,
            @"image_output": imageOutput ?: [NSNull null],
            @"note": textItems.count == 0 ? @"No OCR text detected in the captured window." : [NSNull null],
        };
        print_json(payload);
        CGImageRelease(imageRef);
        CFRelease(imageSource);
        if (shouldDeleteCapture) {
            [[NSFileManager defaultManager] removeItemAtPath:capturePath error:nil];
        }
        return 0;
    }
}
