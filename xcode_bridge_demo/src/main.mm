#import <Cocoa/Cocoa.h>

@interface DemoAppDelegate : NSObject <NSApplicationDelegate>
@property (strong) NSWindow *window;
@end

@implementation DemoAppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification
{
    NSRect frame = NSMakeRect(0, 0, 420, 220);
    NSWindowStyleMask style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable;
    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:style
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    [self.window center];
    [self.window setTitle:@"VS Code <-> CMake <-> Xcode bridge"];

    NSTextField *label = [[NSTextField alloc] initWithFrame:NSMakeRect(20, 120, 380, 24)];
    [label setStringValue:@"If you can see this window, the bridge works."];
    [label setBezeled:NO];
    [label setDrawsBackground:NO];
    [label setEditable:NO];
    [label setSelectable:NO];
    [[self.window contentView] addSubview:label];

    NSButton *button = [[NSButton alloc] initWithFrame:NSMakeRect(20, 70, 140, 32)];
    [button setTitle:@"OK"];
    [button setBezelStyle:NSBezelStyleRounded];
    [button setTarget:NSApp];
    [button setAction:@selector(terminate:)];
    [[self.window contentView] addSubview:button];

    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

@end

int main(int argc, const char *argv[])
{
    @autoreleasepool
    {
        NSApplication *app = [NSApplication sharedApplication];
        DemoAppDelegate *delegate = [[DemoAppDelegate alloc] init];
        [app setDelegate:delegate];
        return NSApplicationMain(argc, argv);
    }
}
