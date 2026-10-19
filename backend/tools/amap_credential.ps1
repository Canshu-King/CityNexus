# Shared Windows Credential Manager helper for the CityNexus Amap key. Dot-sourced by
# amap_key_setup.ps1 and amap_key_run_backend.ps1, so the marshalling exists once. ASCII only: Windows
# PowerShell 5.1 reads a BOM-less .ps1 as ANSI and a CJK character would swallow the quotes after it.
#
# Nothing here prints a secret. Set takes the value in memory, Get returns it in memory, and the only
# thing ever written out is the length.

$script:AmapCredentialTarget = 'CityNexus.Amap.WebService'

if (-not ('CityNexusCred.Store' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

namespace CityNexusCred
{
    public static class Store
    {
        private const int Generic = 1;
        private const int PersistLocalMachine = 2;

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private class Credential
        {
            public int Flags;
            public int Type;
            [MarshalAs(UnmanagedType.LPWStr)] public string TargetName;
            [MarshalAs(UnmanagedType.LPWStr)] public string Comment;
            public long LastWritten;
            public int CredentialBlobSize;
            public IntPtr CredentialBlob;
            public int Persist;
            public int AttributeCount;
            public IntPtr Attributes;
            [MarshalAs(UnmanagedType.LPWStr)] public string TargetUserName;
        }

        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern bool CredWriteW(Credential credential, int flags);

        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern bool CredReadW(string target, int type, int flags, out IntPtr handle);

        [DllImport("advapi32.dll")]
        private static extern void CredFree(IntPtr buffer);

        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern bool CredDeleteW(string target, int type, int flags);

        public static void Set(string target, string userName, string comment, string secret)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(secret);
            IntPtr blob = Marshal.AllocHGlobal(bytes.Length);
            try
            {
                Marshal.Copy(bytes, 0, blob, bytes.Length);
                Credential credential = new Credential();
                credential.Type = Generic;
                credential.TargetName = target;
                credential.Comment = comment;
                credential.CredentialBlobSize = bytes.Length;
                credential.CredentialBlob = blob;
                credential.Persist = PersistLocalMachine;
                credential.TargetUserName = userName;
                if (!CredWriteW(credential, 0))
                {
                    throw new InvalidOperationException("CredWrite failed, win32 error " + Marshal.GetLastWin32Error());
                }
            }
            finally
            {
                Marshal.FreeHGlobal(blob);
            }
        }

        public static string TryGet(string target)
        {
            IntPtr handle;
            if (!CredReadW(target, Generic, 0, out handle))
            {
                return null;
            }
            try
            {
                Credential credential = (Credential)Marshal.PtrToStructure(handle, typeof(Credential));
                byte[] bytes = new byte[credential.CredentialBlobSize];
                Marshal.Copy(credential.CredentialBlob, bytes, 0, bytes.Length);
                return Encoding.UTF8.GetString(bytes);
            }
            finally
            {
                CredFree(handle);
            }
        }

        public static bool Delete(string target)
        {
            return CredDeleteW(target, Generic, 0);
        }
    }
}
'@
}

function Set-AmapKey {
    param([string]$Secret, [string]$Target = $script:AmapCredentialTarget)
    [CityNexusCred.Store]::Set($Target, 'citynexus-backend', 'CityNexus server-side Amap key; never sent to the browser', $Secret)
}

function Get-AmapKey {
    param([string]$Target = $script:AmapCredentialTarget)
    return [CityNexusCred.Store]::TryGet($Target)
}

function Remove-AmapKey {
    param([string]$Target = $script:AmapCredentialTarget)
    return [CityNexusCred.Store]::Delete($Target)
}
