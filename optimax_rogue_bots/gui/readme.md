# OR Client Connected Bots

This package is used for bots that are connected to the optimax rogue client graphical user interface
through a TCP connection. The graphical interface is implemented in C#. This is implemented through a
filtered connection; the native code connects to the server and the bot code connects to the native code.
Additional packets are sent between the GUI and the bot for visual effects and training purposes, but
the actual game packets (and moves) are still passed through to the bot, allowing generic bot implementations
to be extended rather than replaced when using this API.