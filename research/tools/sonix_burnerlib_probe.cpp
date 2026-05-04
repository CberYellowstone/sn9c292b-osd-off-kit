// Read-only probe for SONiX BurnerApLib.dll.
//
// This executable intentionally does not resolve or call erase/write/burn APIs.
// It only checks whether a vendor BurnerApLib can initialize its device layer
// and read basic identification/status fields from the currently attached camera.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static std::wstring LastErrorText(DWORD error) {
    wchar_t *buffer = nullptr;
    DWORD flags = FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
                  FORMAT_MESSAGE_IGNORE_INSERTS;
    DWORD count = FormatMessageW(flags, nullptr, error, 0,
                                 reinterpret_cast<wchar_t *>(&buffer), 0, nullptr);
    std::wstring text;
    if (count && buffer) {
        text.assign(buffer, count);
        while (!text.empty() && (text.back() == L'\r' || text.back() == L'\n')) {
            text.pop_back();
        }
    } else {
        std::wstringstream ss;
        ss << L"Win32 error " << error;
        text = ss.str();
    }
    if (buffer) LocalFree(buffer);
    return text;
}

static std::wstring DirName(const std::wstring &path) {
    size_t slash = path.find_last_of(L"\\/");
    if (slash == std::wstring::npos) return L".";
    return path.substr(0, slash);
}

static std::string Narrow(const std::wstring &value) {
    if (value.empty()) return {};
    int needed = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), -1, nullptr, 0,
                                     nullptr, nullptr);
    if (needed <= 0) return {};
    std::string out(static_cast<size_t>(needed - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.c_str(), -1, out.data(), needed,
                        nullptr, nullptr);
    return out;
}

static void PrintBytes(const char *label, const unsigned char *data, size_t len) {
    std::cout << label << ":";
    for (size_t i = 0; i < len; ++i) {
        std::cout << ' ' << std::hex << std::uppercase << std::setw(2)
                  << std::setfill('0') << static_cast<unsigned int>(data[i]);
    }
    std::cout << std::dec << std::setfill(' ') << "\n";
}

template <typename Fn, typename... Args>
static bool SafeCall(const char *label, Fn fn, Args... args) {
    if (!fn) {
        std::cout << label << ": missing\n";
        return false;
    }

    __try {
        auto result = fn(args...);
        std::cout << label << ": result=" << static_cast<int>(result) << "\n";
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        std::cout << label << ": exception=0x" << std::hex << std::uppercase
                  << GetExceptionCode() << std::dec << "\n";
        return false;
    }
}

template <typename Fn, typename ResultPrinter, typename... Args>
static bool SafeCallPrint(const char *label, Fn fn, ResultPrinter printer, Args... args) {
    if (!fn) {
        std::cout << label << ": missing\n";
        return false;
    }

    __try {
        auto result = fn(args...);
        std::cout << label << ": result=" << static_cast<int>(result);
        printer();
        std::cout << "\n";
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        std::cout << label << ": exception=0x" << std::hex << std::uppercase
                  << GetExceptionCode() << std::dec << "\n";
        return false;
    }
}

static FARPROC Resolve(HMODULE dll, const char *name) {
    FARPROC proc = GetProcAddress(dll, name);
    std::cout << "export " << name << ": " << (proc ? "present" : "missing") << "\n";
    return proc;
}

static int ProbeAmcrest(HMODULE dll) {
    using Init2 = int (__cdecl *)(int, int);
    using Uninit1 = bool (__cdecl *)(int);
    using GetRomVersion1 = bool (__cdecl *)(int, char *);
    using GetMemType1 = bool (__cdecl *)(int, unsigned char *);
    using GetFlashType1 = int (__cdecl *)(int);
    using GetSFStatus1 = bool (__cdecl *)(int, unsigned char *);
    using GetSFSize1 = bool (__cdecl *)(int, unsigned long *, unsigned long *);
    using GetDevLocation1 = bool (__cdecl *)(int, char *);
    using GetCodeVersion1 = bool (__cdecl *)(int, unsigned char *);

    auto init = reinterpret_cast<Init2>(
        Resolve(dll, "?Initialize_DriverInterface@@YAHHH@Z"));
    auto uninit = reinterpret_cast<Uninit1>(
        Resolve(dll, "?UnInitialize_DriverInterface@@YA_NH@Z"));
    auto getRom = reinterpret_cast<GetRomVersion1>(
        Resolve(dll, "?GetRomVersion@@YA_NHPAD@Z"));
    auto getMem = reinterpret_cast<GetMemType1>(
        Resolve(dll, "?GetMemType@@YA_NHPAE@Z"));
    auto getFlashType = reinterpret_cast<GetFlashType1>(
        Resolve(dll, "?GetFlashType@@YAHH@Z"));
    auto getSfStatus = reinterpret_cast<GetSFStatus1>(
        Resolve(dll, "?GetSFStatus@@YA_NHPAE@Z"));
    auto getSfSize = reinterpret_cast<GetSFSize1>(
        Resolve(dll, "?GetSFSize@@YA_NHPAK0@Z"));
    auto getDevLocation = reinterpret_cast<GetDevLocation1>(
        Resolve(dll, "?GetDevLocation@@YA_NHPAD@Z"));
    auto getCodeVersion = reinterpret_cast<GetCodeVersion1>(
        Resolve(dll, "?GetCodeVersion@@YA_NHPAE@Z"));

    if (!init) {
        std::cout << "amcrest probe: missing known 2-arg initializer\n";
        return 2;
    }

    // Try the two most plausible interface modes without calling write/erase.
    // Device index 0 is the only index touched here.
    for (int mode : {0, 3}) {
        std::cout << "\n[amcrest] Initialize_DriverInterface(device=0, mode="
                  << mode << ")\n";
        bool initCalled = SafeCall("init", init, 0, mode);

        if (initCalled) {
            char rom[256] = {};
            SafeCallPrint("GetRomVersion", getRom, [&]() {
                std::cout << " text=\"" << rom << "\"";
            }, 0, rom);

            char location[256] = {};
            SafeCallPrint("GetDevLocation", getDevLocation, [&]() {
                std::cout << " text=\"" << location << "\"";
            }, 0, location);

            unsigned char memType[16] = {};
            SafeCallPrint("GetMemType", getMem, [&]() {
                PrintBytes(" bytes", memType, sizeof(memType));
            }, 0, memType);

            unsigned char codeVersion[16] = {};
            SafeCallPrint("GetCodeVersion", getCodeVersion, [&]() {
                PrintBytes(" bytes", codeVersion, sizeof(codeVersion));
            }, 0, codeVersion);

            if (getFlashType) {
                __try {
                    int flashType = getFlashType(0);
                    std::cout << "GetFlashType: result=" << flashType << "\n";
                } __except (EXCEPTION_EXECUTE_HANDLER) {
                    std::cout << "GetFlashType: exception=0x" << std::hex
                              << std::uppercase << GetExceptionCode() << std::dec << "\n";
                }
            } else {
                std::cout << "GetFlashType: missing\n";
            }

            unsigned char sfStatus[16] = {};
            SafeCallPrint("GetSFStatus", getSfStatus, [&]() {
                PrintBytes(" bytes", sfStatus, sizeof(sfStatus));
            }, 0, sfStatus);

            unsigned long sfSize0 = 0;
            unsigned long sfSize1 = 0;
            SafeCallPrint("GetSFSize", getSfSize, [&]() {
                std::cout << " size0=" << sfSize0 << " size1=" << sfSize1;
            }, 0, &sfSize0, &sfSize1);

            SafeCall("uninit", uninit, 0);
        }
    }

    return 0;
}

static int ProbePublic(HMODULE dll) {
    using Init0 = int (__cdecl *)();
    using Uninit0 = bool (__cdecl *)();
    using GetRomVersion0 = bool (__cdecl *)(char *);
    using GetMemType0 = bool (__cdecl *)(unsigned char *);
    using GetSFStatus0 = bool (__cdecl *)(unsigned char *);
    using GetSFSize0 = bool (__cdecl *)(unsigned long *, unsigned long *);
    using GetFlashType0 = int (__cdecl *)();

    auto init = reinterpret_cast<Init0>(
        Resolve(dll, "?Initialize_DriverInterface@@YAHXZ"));
    auto uninit = reinterpret_cast<Uninit0>(
        Resolve(dll, "?UnInitialize_DriverInterface@@YA_NXZ"));
    auto getRom = reinterpret_cast<GetRomVersion0>(
        Resolve(dll, "?GetRomVersion@@YA_NPAD@Z"));
    auto getMem = reinterpret_cast<GetMemType0>(
        Resolve(dll, "?GetMemType@@YA_NPAE@Z"));
    auto getSfStatus = reinterpret_cast<GetSFStatus0>(
        Resolve(dll, "?GetSFStatus@@YA_NPAE@Z"));
    auto getSfSize = reinterpret_cast<GetSFSize0>(
        Resolve(dll, "?GetSFSize@@YA_NPAK0@Z"));
    auto getFlashType = reinterpret_cast<GetFlashType0>(
        Resolve(dll, "?GetFlashType@@YAHXZ"));

    if (!init) {
        std::cout << "public probe: missing known no-arg initializer\n";
        return 2;
    }

    std::cout << "\n[public] Initialize_DriverInterface()\n";
    bool initCalled = SafeCall("init", init);
    if (!initCalled) return 3;

    char rom[256] = {};
    SafeCallPrint("GetRomVersion", getRom, [&]() {
        std::cout << " text=\"" << rom << "\"";
    }, rom);

    unsigned char memType[16] = {};
    SafeCallPrint("GetMemType", getMem, [&]() {
        PrintBytes(" bytes", memType, sizeof(memType));
    }, memType);

    if (getFlashType) {
        __try {
            int flashType = getFlashType();
            std::cout << "GetFlashType: result=" << flashType << "\n";
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            std::cout << "GetFlashType: exception=0x" << std::hex << std::uppercase
                      << GetExceptionCode() << std::dec << "\n";
        }
    } else {
        std::cout << "GetFlashType: missing\n";
    }

    unsigned char sfStatus[16] = {};
    SafeCallPrint("GetSFStatus", getSfStatus, [&]() {
        PrintBytes(" bytes", sfStatus, sizeof(sfStatus));
    }, sfStatus);

    unsigned long sfSize0 = 0;
    unsigned long sfSize1 = 0;
    SafeCallPrint("GetSFSize", getSfSize, [&]() {
        std::cout << " size0=" << sfSize0 << " size1=" << sfSize1;
    }, &sfSize0, &sfSize1);

    SafeCall("uninit", uninit);
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    if (argc < 2) {
        std::wcerr << L"usage: sonix_burnerlib_probe.exe <BurnerApLib.dll> [amcrest|public]\n";
        return 64;
    }

    std::wstring dllPath = argv[1];
    std::string mode = argc >= 3 ? Narrow(argv[2]) : "auto";

    SetDllDirectoryW(DirName(dllPath).c_str());

    HMODULE dll = LoadLibraryW(dllPath.c_str());
    if (!dll) {
        DWORD error = GetLastError();
        std::wcerr << L"LoadLibrary failed: " << LastErrorText(error) << L"\n";
        return 1;
    }

    std::wcout << L"loaded: " << dllPath << L"\n";
    std::cout << "mode: " << mode << "\n";

    FARPROC amcrestMarker = GetProcAddress(dll, "?Initialize_DriverInterface@@YAHHH@Z");
    FARPROC publicMarker = GetProcAddress(dll, "?Initialize_DriverInterface@@YAHXZ");

    int rc = 0;
    if (mode == "amcrest" || (mode == "auto" && amcrestMarker)) {
        rc = ProbeAmcrest(dll);
    } else if (mode == "public" || (mode == "auto" && publicMarker)) {
        rc = ProbePublic(dll);
    } else {
        std::cout << "No known read-only initializer signature found.\n";
        rc = 2;
    }

    FreeLibrary(dll);
    return rc;
}
