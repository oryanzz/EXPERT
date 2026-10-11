# Creates an "EXPERT" shortcut that starts the app without a console window.
# Default location is the desktop; pass -Dir to put it somewhere else.
param([string]$Dir = [Environment]::GetFolderPath('Desktop'))

$root = Split-Path -Parent $PSScriptRoot
$appId = 'ORYANZ.EXPERT'  # must match APP_ID in app.py
$path = Join-Path $Dir 'EXPERT.lnk'

$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($path)
$link.TargetPath = Join-Path $root '.venv\Scripts\pythonw.exe'
$link.Arguments = '"' + (Join-Path $root 'app.py') + '"'
$link.WorkingDirectory = $root
$link.IconLocation = (Join-Path $root 'ui\icon.ico') + ',0'
$link.Description = 'EXPERT - EXP PER TIME'
$link.Save()

# Stamp the app's taskbar identity (AppUserModelID) on the shortcut, so a pinned EXPERT and the
# running window share one taskbar button with the EXPERT icon instead of Python's.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class ShortcutAppId {
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PROPERTYKEY { public Guid fmtid; public uint pid; }

    [StructLayout(LayoutKind.Explicit, Size = 24)]
    struct PROPVARIANT { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr ptr; }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        void GetCount(out uint count);
        void GetAt(uint index, out PROPERTYKEY key);
        void GetValue(ref PROPERTYKEY key, out PROPVARIANT value);
        void SetValue(ref PROPERTYKEY key, ref PROPVARIANT value);
        void Commit();
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    static extern void SHGetPropertyStoreFromParsingName(string path, IntPtr bindCtx, int flags,
                                                         ref Guid riid, out IPropertyStore store);
    [DllImport("ole32.dll")]
    static extern int PropVariantClear(ref PROPVARIANT pv);

    // PKEY_AppUserModel_ID
    static PROPERTYKEY Key() {
        return new PROPERTYKEY { fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), pid = 5 };
    }

    static IPropertyStore Open(string path, int flags) {
        Guid iid = typeof(IPropertyStore).GUID;
        IPropertyStore store;
        SHGetPropertyStoreFromParsingName(path, IntPtr.Zero, flags, ref iid, out store);
        return store;
    }

    public static void Set(string path, string appId) {
        IPropertyStore store = Open(path, 2);  // GPS_READWRITE
        PROPERTYKEY key = Key();
        PROPVARIANT pv = new PROPVARIANT { vt = 31, ptr = Marshal.StringToCoTaskMemUni(appId) };  // VT_LPWSTR
        try { store.SetValue(ref key, ref pv); store.Commit(); }
        finally { PropVariantClear(ref pv); Marshal.ReleaseComObject(store); }
    }

    public static string Get(string path) {
        IPropertyStore store = Open(path, 0);  // GPS_DEFAULT
        PROPERTYKEY key = Key();
        PROPVARIANT pv;
        try {
            store.GetValue(ref key, out pv);
            string value = pv.vt == 31 ? Marshal.PtrToStringUni(pv.ptr) : null;
            PropVariantClear(ref pv);
            return value;
        }
        finally { Marshal.ReleaseComObject(store); }
    }
}
'@
[ShortcutAppId]::Set($path, $appId)
Write-Host "Shortcut created: $path"
