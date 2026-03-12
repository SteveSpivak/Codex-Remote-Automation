#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>

static void print_result(NSDictionary *payload, int exit_code) {
  NSError *error = nil;
  NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:&error];
  if (!json) {
    NSString *fallback = [NSString stringWithFormat:@"{\"status\":\"error\",\"note\":\"%s\"}\n", [[error localizedDescription] UTF8String]];
    fwrite([fallback UTF8String], 1, [fallback lengthOfBytesUsingEncoding:NSUTF8StringEncoding], stdout);
    exit(1);
  }
  fwrite([json bytes], 1, [json length], stdout);
  fwrite("\n", 1, 1, stdout);
  exit(exit_code);
}

int main(int argc, const char *argv[]) {
  @autoreleasepool {
    NSString *bundleId = @"com.openai.codex";
    NSString *appName = @"Codex";
    pid_t explicitPid = 0;
    BOOL promptTrust = NO;
    for (int index = 1; index < argc; index++) {
      if (strcmp(argv[index], "--bundle-id") == 0 && index + 1 < argc) {
        bundleId = [NSString stringWithUTF8String:argv[index + 1]];
        index++;
      }
      if (strcmp(argv[index], "--app-name") == 0 && index + 1 < argc) {
        appName = [NSString stringWithUTF8String:argv[index + 1]];
        index++;
      }
      if (strcmp(argv[index], "--pid") == 0 && index + 1 < argc) {
        explicitPid = (pid_t)strtol(argv[index + 1], NULL, 10);
        index++;
      }
      if (strcmp(argv[index], "--prompt-trust") == 0) {
        promptTrust = YES;
      }
    }

    NSDictionary *trustOptions = nil;
    if (promptTrust) {
      trustOptions = @{(__bridge NSString *)kAXTrustedCheckOptionPrompt: @YES};
    }
    BOOL isTrusted = AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)trustOptions);

    pid_t targetPid = explicitPid;
    if (targetPid == 0) {
      NSArray<NSRunningApplication *> *runningApps = [NSRunningApplication runningApplicationsWithBundleIdentifier:bundleId];
      NSRunningApplication *app = [runningApps firstObject];
      if (!app) {
        for (NSRunningApplication *candidate in [[NSWorkspace sharedWorkspace] runningApplications]) {
          if ([[candidate localizedName] isEqualToString:appName]) {
            app = candidate;
            break;
          }
        }
      }

      if (app) {
        targetPid = app.processIdentifier;
      }
    }

    if (targetPid == 0) {
      print_result(@{
        @"status": @"error",
        @"bundleId": bundleId,
        @"appName": appName,
        @"note": @"No running application found for the requested bundle identifier, app name, or PID."
      }, 1);
    }

    AXUIElementRef appRef = AXUIElementCreateApplication(targetPid);
    CFStringRef attributeName = CFSTR("AXManualAccessibility");
    AXError setError = AXUIElementSetAttributeValue(appRef, attributeName, kCFBooleanTrue);

    CFTypeRef currentValue = NULL;
    AXError copyError = AXUIElementCopyAttributeValue(appRef, attributeName, &currentValue);
    NSString *valueString = nil;
    if (copyError == kAXErrorSuccess && currentValue != NULL) {
      if (CFGetTypeID(currentValue) == CFBooleanGetTypeID()) {
        valueString = CFBooleanGetValue((CFBooleanRef)currentValue) ? @"true" : @"false";
      } else {
        valueString = [(__bridge id)currentValue description];
      }
      CFRelease(currentValue);
    }

    NSDictionary *payload = @{
      @"status": (setError == kAXErrorSuccess ? @"ok" : @"error"),
      @"bundleId": bundleId,
      @"appName": appName,
      @"pid": @(targetPid),
      @"isTrusted": @(isTrusted),
      @"axError": @((int)setError),
      @"note": (setError == kAXErrorSuccess
                  ? @"AXManualAccessibility set on the running app process."
                  : @"AXManualAccessibility could not be set. See axError."),
      @"manualAccessibilityValue": (valueString ?: [NSNull null])
    };

    if (appRef != NULL) {
      CFRelease(appRef);
    }

    print_result(payload, (setError == kAXErrorSuccess ? 0 : 1));
  }
}
