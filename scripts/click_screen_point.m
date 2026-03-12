#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>

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

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSNumber *x = nil;
        NSNumber *y = nil;

        for (int i = 1; i < argc; i += 1) {
            NSString *argument = [NSString stringWithUTF8String:argv[i]];
            if ([argument isEqualToString:@"--x"] && i + 1 < argc) {
                x = @([[NSString stringWithUTF8String:argv[++i]] doubleValue]);
            } else if ([argument isEqualToString:@"--y"] && i + 1 < argc) {
                y = @([[NSString stringWithUTF8String:argv[++i]] doubleValue]);
            }
        }

        if (x == nil || y == nil) {
            print_json(@{
                @"status": @"error",
                @"x": x ?: [NSNull null],
                @"y": y ?: [NSNull null],
                @"note": @"Both --x and --y are required.",
            });
            return 1;
        }

        CGPoint point = CGPointMake(x.doubleValue, y.doubleValue);
        CGEventSourceRef source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState);
        CGEventRef mouseDown = CGEventCreateMouseEvent(source, kCGEventLeftMouseDown, point, kCGMouseButtonLeft);
        CGEventRef mouseUp = CGEventCreateMouseEvent(source, kCGEventLeftMouseUp, point, kCGMouseButtonLeft);

        if (mouseDown == nil || mouseUp == nil) {
            if (mouseDown != nil) {
                CFRelease(mouseDown);
            }
            if (mouseUp != nil) {
                CFRelease(mouseUp);
            }
            if (source != nil) {
                CFRelease(source);
            }

            print_json(@{
                @"status": @"error",
                @"x": x,
                @"y": y,
                @"note": @"Failed to create mouse events. Accessibility permission may be required.",
            });
            return 2;
        }

        CGEventPost(kCGHIDEventTap, mouseDown);
        CGEventPost(kCGHIDEventTap, mouseUp);

        CFRelease(mouseDown);
        CFRelease(mouseUp);
        if (source != nil) {
            CFRelease(source);
        }

        print_json(@{
            @"status": @"ok",
            @"x": x,
            @"y": y,
            @"note": [NSNull null],
        });
        return 0;
    }
}
