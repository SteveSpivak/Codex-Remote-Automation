#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>

static id value_for_attribute(AXUIElementRef element, CFStringRef attribute) {
  CFTypeRef value = NULL;
  AXError error = AXUIElementCopyAttributeValue(element, attribute, &value);
  if (error != kAXErrorSuccess || value == NULL) {
    return [NSNull null];
  }

  id bridged = CFBridgingRelease(value);
  return bridged ?: [NSNull null];
}

static NSArray<NSString *> *attribute_names_for_element(AXUIElementRef element) {
  CFArrayRef namesRef = NULL;
  AXError error = AXUIElementCopyAttributeNames(element, &namesRef);
  if (error != kAXErrorSuccess || namesRef == NULL) {
    return @[];
  }
  return CFBridgingRelease(namesRef);
}

static NSString *string_for_value(id value) {
  if (value == nil || value == [NSNull null]) {
    return @"";
  }
  if ([value isKindOfClass:[NSString class]]) {
    return (NSString *)value;
  }
  return [value description];
}

static NSDictionary *snapshot_element(AXUIElementRef element, NSInteger depth, NSInteger maxDepth, NSInteger maxChildren) {
  NSMutableDictionary *node = [NSMutableDictionary dictionary];
  NSArray<NSString *> *attributeNames = attribute_names_for_element(element);
  node[@"role"] = string_for_value(value_for_attribute(element, kAXRoleAttribute));
  node[@"subrole"] = string_for_value(value_for_attribute(element, kAXSubroleAttribute));
  node[@"title"] = string_for_value(value_for_attribute(element, kAXTitleAttribute));
  node[@"description"] = string_for_value(value_for_attribute(element, kAXDescriptionAttribute));
  node[@"help"] = string_for_value(value_for_attribute(element, kAXHelpAttribute));
  node[@"identifier"] = string_for_value(value_for_attribute(element, CFSTR("AXIdentifier")));
  node[@"attributeNames"] = attributeNames;

  if (depth >= maxDepth) {
    node[@"children"] = @[];
    return node;
  }

  NSMutableArray *children = [NSMutableArray array];
  NSArray<NSString *> *relationshipAttributes = @[
    (__bridge NSString *)kAXChildrenAttribute,
    @"AXContents",
    @"AXVisibleChildren"
  ];
  for (NSString *attributeName in relationshipAttributes) {
    id attributeValue = value_for_attribute(element, (__bridge CFStringRef)attributeName);
    if (![attributeValue isKindOfClass:[NSArray class]]) {
      continue;
    }
    for (id child in (NSArray *)attributeValue) {
      if (CFGetTypeID((__bridge CFTypeRef)child) != AXUIElementGetTypeID()) {
        continue;
      }
      [children addObject:child];
    }
  }

  NSMutableArray *childSnapshots = [NSMutableArray array];
  NSInteger limit = MIN((NSInteger)[children count], maxChildren);
  for (NSInteger index = 0; index < limit; index++) {
    id child = children[index];
    [childSnapshots addObject:snapshot_element((__bridge AXUIElementRef)child, depth + 1, maxDepth, maxChildren)];
  }
  node[@"children"] = childSnapshots;
  return node;
}

static void print_json(id payload, int exitCode) {
  NSError *error = nil;
  NSData *data = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:&error];
  if (!data) {
    NSString *fallback = [NSString stringWithFormat:@"{\"status\":\"error\",\"note\":\"%s\"}\n", [[error localizedDescription] UTF8String]];
    fwrite([fallback UTF8String], 1, [fallback lengthOfBytesUsingEncoding:NSUTF8StringEncoding], stdout);
    exit(1);
  }
  fwrite([data bytes], 1, [data length], stdout);
  fwrite("\n", 1, 1, stdout);
  exit(exitCode);
}

int main(int argc, const char *argv[]) {
  @autoreleasepool {
    pid_t pid = 0;
    NSInteger maxDepth = 4;
    NSInteger maxChildren = 20;

    for (int index = 1; index < argc; index++) {
      if (strcmp(argv[index], "--pid") == 0 && index + 1 < argc) {
        pid = (pid_t)strtol(argv[index + 1], NULL, 10);
        index++;
      } else if (strcmp(argv[index], "--max-depth") == 0 && index + 1 < argc) {
        maxDepth = strtol(argv[index + 1], NULL, 10);
        index++;
      } else if (strcmp(argv[index], "--max-children") == 0 && index + 1 < argc) {
        maxChildren = strtol(argv[index + 1], NULL, 10);
        index++;
      }
    }

    if (pid == 0) {
      print_json(@{@"status": @"error", @"note": @"A --pid value is required."}, 1);
    }

    AXUIElementRef appRef = AXUIElementCreateApplication(pid);
    id windowsValue = value_for_attribute(appRef, kAXWindowsAttribute);
    NSMutableArray *windowSnapshots = [NSMutableArray array];

    if ([windowsValue isKindOfClass:[NSArray class]]) {
      for (id window in (NSArray *)windowsValue) {
        if (CFGetTypeID((__bridge CFTypeRef)window) != AXUIElementGetTypeID()) {
          continue;
        }
        [windowSnapshots addObject:snapshot_element((__bridge AXUIElementRef)window, 0, maxDepth, maxChildren)];
      }
    }

    NSDictionary *payload = @{
      @"status": @"ok",
      @"pid": @(pid),
      @"windowCount": @([windowSnapshots count]),
      @"windows": windowSnapshots
    };

    if (appRef != NULL) {
      CFRelease(appRef);
    }

    print_json(payload, 0);
  }
}
