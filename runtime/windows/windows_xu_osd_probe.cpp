// Windows UVC Extension Unit probe for SONiX SN9C292A/B OSD enable control.
//
// This talks through usbvideo.sys / KS, so it does not require Zadig,
// WinUSB, libusb, PyUSB, or firmware flashing.

#define INITGUID
#include <windows.h>
#include <dshow.h>
#include <ks.h>
#include <ksmedia.h>
#include <ksproxy.h>
#include <vidcap.h>

#include <iomanip>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdio>

// From SONiX_UVC_TestAP sonix_xu_ctrls.h:
// {94 73 DF DD 3E 97 27 47 BE D9 04 ED 64 26 DC 67}
// DEFINE_GUID uses the first three fields in native integer order.
DEFINE_GUID(PROPSETID_SONIX_USR_XU,
            0xDDDF7394, 0x973E, 0x4727,
            0xBE, 0xD9, 0x04, 0xED, 0x64, 0x26, 0xDC, 0x67);

// From SONiX_UVC_TestAP sonix_xu_ctrls.h:
// {70 33 F0 28 11 63 2E 4A BA 2C 68 90 EB 33 40 16}
DEFINE_GUID(PROPSETID_SONIX_SYS_XU,
            0x28F03370, 0x6311, 0x4A2E,
            0xBA, 0x2C, 0x68, 0x90, 0xEB, 0x33, 0x40, 0x16);

static constexpr ULONG SONIX_USR_OSD_CTRL_SELECTOR = 0x04;
static constexpr ULONG SONIX_SYS_ASIC_RW_SELECTOR = 0x01;
static constexpr ULONG SONIX_SYS_FLASH_CTRL_SELECTOR = 0x03;
static constexpr ULONG SONIX_SYS_FLASH_STATUS_SELECTOR = 0x05;
static constexpr ULONG SONIX_SYS_ALT_SPI_READ_SET_SELECTOR = 0x23;
static constexpr ULONG SONIX_SYS_ALT_SPI_READ_GET_SELECTOR = 0x24;
static constexpr ULONG XU_PAYLOAD_SIZE = 11;

template <class T>
static void SafeRelease(T **pp) {
    if (pp && *pp) {
        (*pp)->Release();
        *pp = nullptr;
    }
}

static std::wstring HresultText(HRESULT hr) {
    std::wstringstream ss;
    ss << L"0x" << std::hex << std::uppercase << static_cast<unsigned long>(hr);
    return ss.str();
}

static std::wstring GuidText(const GUID &g) {
    wchar_t buf[64] = {};
    StringFromGUID2(g, buf, 64);
    return buf;
}

static bool EqualsIgnoreCase(const std::wstring &s, const wchar_t *needle) {
    std::wstring lower = s;
    for (auto &ch : lower) ch = static_cast<wchar_t>(towlower(ch));
    std::wstring n = needle;
    for (auto &ch : n) ch = static_cast<wchar_t>(towlower(ch));
    return lower.find(n) != std::wstring::npos;
}

static std::wstring ReadBagString(IPropertyBag *bag, const wchar_t *name) {
    VARIANT var;
    VariantInit(&var);
    std::wstring out;
    if (SUCCEEDED(bag->Read(name, &var, nullptr)) && var.vt == VT_BSTR && var.bstrVal) {
        out = var.bstrVal;
    }
    VariantClear(&var);
    return out;
}

static HRESULT KsProperty(IKsControl *ks, const GUID &set, ULONG nodeId,
                          ULONG propId, ULONG flags, BYTE *data, ULONG dataLen,
                          ULONG *bytesReturned = nullptr) {
    KSP_NODE prop = {};
    prop.Property.Set = set;
    prop.Property.Id = propId;
    prop.Property.Flags = flags | KSPROPERTY_TYPE_TOPOLOGY;
    prop.NodeId = nodeId;

    ULONG returned = 0;
    HRESULT hr = ks->KsProperty(reinterpret_cast<PKSPROPERTY>(&prop),
                                sizeof(prop), data, dataLen, &returned);
    if (bytesReturned) {
        *bytesReturned = returned;
    }
    return hr;
}

static void PrintBytes(const BYTE *data, ULONG len) {
    for (ULONG i = 0; i < len; ++i) {
        if (i) std::wcout << L' ';
        std::wcout << std::hex << std::uppercase << std::setw(2) << std::setfill(L'0')
                   << static_cast<unsigned int>(data[i]);
    }
    std::wcout << std::dec << std::setfill(L' ') << L"\n";
}

static HRESULT FindSonixCamera(IBaseFilter **filterOut, std::wstring *nameOut,
                               std::wstring *pathOut) {
    *filterOut = nullptr;

    ICreateDevEnum *devEnum = nullptr;
    IEnumMoniker *enumMoniker = nullptr;

    HRESULT hr = CoCreateInstance(CLSID_SystemDeviceEnum, nullptr, CLSCTX_INPROC_SERVER,
                                  IID_PPV_ARGS(&devEnum));
    if (FAILED(hr)) return hr;

    hr = devEnum->CreateClassEnumerator(CLSID_VideoInputDeviceCategory, &enumMoniker, 0);
    if (hr != S_OK) {
        SafeRelease(&devEnum);
        return hr;
    }

    IMoniker *moniker = nullptr;
    std::wcout << L"DirectShow video input candidates:\n";
    while (enumMoniker->Next(1, &moniker, nullptr) == S_OK) {
        IPropertyBag *bag = nullptr;
        std::wstring friendlyName;
        std::wstring devicePath;

        if (SUCCEEDED(moniker->BindToStorage(nullptr, nullptr, IID_PPV_ARGS(&bag)))) {
            friendlyName = ReadBagString(bag, L"FriendlyName");
            devicePath = ReadBagString(bag, L"DevicePath");
            SafeRelease(&bag);
        }

        std::wcout << L"  name: " << friendlyName << L"\n";
        std::wcout << L"  path: " << devicePath << L"\n";

        bool isTarget = EqualsIgnoreCase(devicePath, L"vid_0c45&pid_6366") ||
                        EqualsIgnoreCase(devicePath, L"0c45") ||
                        EqualsIgnoreCase(devicePath, L"6366") ||
                        EqualsIgnoreCase(friendlyName, L"292a") ||
                        EqualsIgnoreCase(friendlyName, L"ov2710") ||
                        EqualsIgnoreCase(friendlyName, L"usb camera") ||
                        EqualsIgnoreCase(friendlyName, L"usb 2.0 camera");
        if (isTarget) {
            IBaseFilter *filter = nullptr;
            hr = moniker->BindToObject(nullptr, nullptr, IID_PPV_ARGS(&filter));
            if (SUCCEEDED(hr)) {
                *filterOut = filter;
                if (nameOut) *nameOut = friendlyName;
                if (pathOut) *pathOut = devicePath;
                SafeRelease(&moniker);
                SafeRelease(&enumMoniker);
                SafeRelease(&devEnum);
                return S_OK;
            }
            std::wcout << L"  target candidate bind failed: " << HresultText(hr) << L"\n";
        }

        SafeRelease(&moniker);
    }

    SafeRelease(&enumMoniker);
    SafeRelease(&devEnum);
    return HRESULT_FROM_WIN32(ERROR_NOT_FOUND);
}

static HRESULT ListNodes(IKsTopologyInfo *topo, std::vector<DWORD> *devSpecificNodes) {
    DWORD nodeCount = 0;
    HRESULT hr = topo->get_NumNodes(&nodeCount);
    if (FAILED(hr)) return hr;

    std::wcout << L"KS node count: " << nodeCount << L"\n";
    for (DWORD node = 0; node < nodeCount; ++node) {
        GUID type = {};
        hr = topo->get_NodeType(node, &type);
        if (FAILED(hr)) {
            std::wcout << L"  node " << node << L": get_NodeType failed "
                       << HresultText(hr) << L"\n";
            continue;
        }
        std::wcout << L"  node " << node << L": " << GuidText(type);
        if (IsEqualGUID(type, PROPSETID_SONIX_USR_XU)) std::wcout << L"  SONIX_USR_XU";
        if (IsEqualGUID(type, PROPSETID_SONIX_SYS_XU)) std::wcout << L"  SONIX_SYS_XU";
        if (IsEqualGUID(type, KSNODETYPE_DEV_SPECIFIC)) {
            std::wcout << L"  DEV_SPECIFIC";
            if (devSpecificNodes) devSpecificNodes->push_back(node);
        }
        std::wcout << L"\n";
    }

    return S_OK;
}

static HRESULT SonixOsdGet(IKsControl *ks, DWORD nodeId, BYTE *line, BYTE *block) {
    BYTE data[XU_PAYLOAD_SIZE] = {};
    data[0] = 0x9A;
    data[1] = 0x04; // C1 tool subcommand: OSD enable

    HRESULT hr = KsProperty(ks, PROPSETID_SONIX_USR_XU, nodeId,
                            SONIX_USR_OSD_CTRL_SELECTOR, KSPROPERTY_TYPE_SET,
                            data, XU_PAYLOAD_SIZE);
    if (FAILED(hr)) return hr;

    ZeroMemory(data, sizeof(data));
    ULONG returned = 0;
    hr = KsProperty(ks, PROPSETID_SONIX_USR_XU, nodeId,
                    SONIX_USR_OSD_CTRL_SELECTOR, KSPROPERTY_TYPE_GET,
                    data, XU_PAYLOAD_SIZE, &returned);
    if (FAILED(hr)) return hr;

    std::wcout << L"raw get bytes (" << returned << L"): ";
    PrintBytes(data, XU_PAYLOAD_SIZE);
    *line = data[0];
    *block = data[1];
    return S_OK;
}

static HRESULT SonixOsdSet(IKsControl *ks, DWORD nodeId, BYTE line, BYTE block) {
    BYTE data[XU_PAYLOAD_SIZE] = {};
    data[0] = 0x9A;
    data[1] = 0x04; // C1 tool subcommand: OSD enable

    HRESULT hr = KsProperty(ks, PROPSETID_SONIX_USR_XU, nodeId,
                            SONIX_USR_OSD_CTRL_SELECTOR, KSPROPERTY_TYPE_SET,
                            data, XU_PAYLOAD_SIZE);
    if (FAILED(hr)) return hr;

    ZeroMemory(data, sizeof(data));
    data[0] = line;
    data[1] = block;
    return KsProperty(ks, PROPSETID_SONIX_USR_XU, nodeId,
                      SONIX_USR_OSD_CTRL_SELECTOR, KSPROPERTY_TYPE_SET,
                      data, XU_PAYLOAD_SIZE);
}

static HRESULT SonixSfRead8(IKsControl *ks, DWORD nodeId, unsigned int addr,
                            BYTE *out, unsigned int len) {
    if (len == 0 || len > 8) {
        return E_INVALIDARG;
    }

    BYTE data[XU_PAYLOAD_SIZE] = {};
    data[0] = static_cast<BYTE>(addr & 0xFF);
    data[1] = static_cast<BYTE>((addr >> 8) & 0xFF);
    data[2] = static_cast<BYTE>(0x80 | ((addr >> 16) ? 0x10 : 0x00) | (len & 0x0F));

    HRESULT hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                            SONIX_SYS_FLASH_CTRL_SELECTOR, KSPROPERTY_TYPE_SET,
                            data, XU_PAYLOAD_SIZE);
    if (FAILED(hr)) return hr;

    ZeroMemory(data, sizeof(data));
    ULONG returned = 0;
    hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                    SONIX_SYS_FLASH_CTRL_SELECTOR, KSPROPERTY_TYPE_GET,
                    data, XU_PAYLOAD_SIZE, &returned);
    if (FAILED(hr)) return hr;

    memcpy(out, data + 3, len);
    return S_OK;
}

static HRESULT SonixSfReadRange(IKsControl *ks, DWORD nodeId, unsigned int addr,
                                unsigned int len, std::vector<BYTE> *out) {
    out->clear();
    out->resize(len);

    unsigned int done = 0;
    while (done < len) {
        unsigned int thisLen = min(8u, len - done);
        HRESULT hr = SonixSfRead8(ks, nodeId, addr + done, out->data() + done, thisLen);
        if (FAILED(hr)) return hr;
        done += thisLen;
    }
    return S_OK;
}

static HRESULT SonixSfWrite8(IKsControl *ks, DWORD nodeId, unsigned int addr,
                             const BYTE *block) {
    if ((addr & 0x7u) != 0) {
        return E_INVALIDARG;
    }

    BYTE data[XU_PAYLOAD_SIZE] = {};
    data[0] = static_cast<BYTE>(addr & 0xFF);
    data[1] = static_cast<BYTE>((addr >> 8) & 0xFF);
    // Official burner sub_AC29D0 uses 0x08 for bank 0 and 0x18 for bank 1.
    data[2] = static_cast<BYTE>((addr >> 16) ? 0x18 : 0x08);
    memcpy(data + 3, block, 8);

    return KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                      SONIX_SYS_FLASH_CTRL_SELECTOR, KSPROPERTY_TYPE_SET,
                      data, XU_PAYLOAD_SIZE);
}

static HRESULT SonixAltSfReadChunk(IKsControl *ks, DWORD nodeId, unsigned int addr,
                                   BYTE *out, unsigned int len) {
    if (len == 0 || len > 1023) {
        return E_INVALIDARG;
    }

    BYTE setData[5] = {};
    setData[0] = static_cast<BYTE>((addr >> 16) & 0xFF);
    setData[1] = static_cast<BYTE>((addr >> 8) & 0xFF);
    setData[2] = static_cast<BYTE>(addr & 0xFF);
    setData[3] = static_cast<BYTE>((len >> 8) & 0xFF);
    setData[4] = static_cast<BYTE>(len & 0xFF);

    HRESULT hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                            SONIX_SYS_ALT_SPI_READ_SET_SELECTOR, KSPROPERTY_TYPE_SET,
                            setData, sizeof(setData));
    if (FAILED(hr)) return hr;

    ULONG returned = 0;
    hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                    SONIX_SYS_ALT_SPI_READ_GET_SELECTOR, KSPROPERTY_TYPE_GET,
                    out, len, &returned);
    if (FAILED(hr)) return hr;
    return returned == len ? S_OK : HRESULT_FROM_WIN32(ERROR_INVALID_DATA);
}

static HRESULT SonixAltSfReadRange(IKsControl *ks, DWORD nodeId, unsigned int addr,
                                   unsigned int len, std::vector<BYTE> *out) {
    out->clear();
    out->resize(len);

    unsigned int done = 0;
    while (done < len) {
        unsigned int thisLen = min(1023u, len - done);
        HRESULT hr = SonixAltSfReadChunk(ks, nodeId, addr + done,
                                         out->data() + done, thisLen);
        if (FAILED(hr)) return hr;
        done += thisLen;
    }
    return S_OK;
}

static HRESULT SonixAsicRead(IKsControl *ks, DWORD nodeId, unsigned int addr, BYTE *value) {
    BYTE data[4] = {};
    data[0] = static_cast<BYTE>(addr & 0xFF);
    data[1] = static_cast<BYTE>((addr >> 8) & 0xFF);
    data[2] = 0x00;
    data[3] = 0xFF; // dummy write before read

    HRESULT hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                            SONIX_SYS_ASIC_RW_SELECTOR, KSPROPERTY_TYPE_SET,
                            data, sizeof(data));
    if (FAILED(hr)) return hr;

    data[3] = 0x00;
    hr = KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                    SONIX_SYS_ASIC_RW_SELECTOR, KSPROPERTY_TYPE_GET,
                    data, sizeof(data));
    if (FAILED(hr)) return hr;

    *value = data[2];
    return S_OK;
}

static HRESULT SonixAsicWrite(IKsControl *ks, DWORD nodeId, unsigned int addr, BYTE value) {
    BYTE data[4] = {};
    data[0] = static_cast<BYTE>(addr & 0xFF);
    data[1] = static_cast<BYTE>((addr >> 8) & 0xFF);
    data[2] = value;
    data[3] = 0x00;

    return KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                      SONIX_SYS_ASIC_RW_SELECTOR, KSPROPERTY_TYPE_SET,
                      data, sizeof(data));
}

static HRESULT SonixAsicReadRange(IKsControl *ks, DWORD nodeId, unsigned int addr,
                                  unsigned int len, std::vector<BYTE> *out) {
    out->clear();
    out->resize(len);
    for (unsigned int i = 0; i < len; ++i) {
        HRESULT hr = SonixAsicRead(ks, nodeId, addr + i, out->data() + i);
        if (FAILED(hr)) return hr;
    }
    return S_OK;
}

static bool LoadBinaryFile(const std::wstring &path, std::vector<BYTE> *out,
                           std::wstring *error) {
    FILE *fp = nullptr;
    if (_wfopen_s(&fp, path.c_str(), L"rb") != 0 || !fp) {
        if (error) *error = L"cannot open file";
        return false;
    }

    if (_fseeki64(fp, 0, SEEK_END) != 0) {
        if (error) *error = L"cannot seek file";
        fclose(fp);
        return false;
    }

    __int64 size = _ftelli64(fp);
    if (size < 0) {
        if (error) *error = L"cannot get file size";
        fclose(fp);
        return false;
    }
    if (_fseeki64(fp, 0, SEEK_SET) != 0) {
        if (error) *error = L"cannot rewind file";
        fclose(fp);
        return false;
    }

    out->assign(static_cast<size_t>(size), 0);
    if (size > 0) {
        size_t got = fread(out->data(), 1, static_cast<size_t>(size), fp);
        if (got != static_cast<size_t>(size)) {
            if (error) *error = L"short read";
            fclose(fp);
            return false;
        }
    }

    fclose(fp);
    return true;
}

static bool BytesEqual(const BYTE *a, const BYTE *b, size_t len) {
    return memcmp(a, b, len) == 0;
}

static HRESULT SonixAsicOr(IKsControl *ks, DWORD nodeId, unsigned int addr, BYTE mask) {
    BYTE value = 0;
    HRESULT hr = SonixAsicRead(ks, nodeId, addr, &value);
    if (FAILED(hr)) return hr;
    return SonixAsicWrite(ks, nodeId, addr, static_cast<BYTE>(value | mask));
}

static HRESULT SonixAsicAnd(IKsControl *ks, DWORD nodeId, unsigned int addr, BYTE mask) {
    BYTE value = 0;
    HRESULT hr = SonixAsicRead(ks, nodeId, addr, &value);
    if (FAILED(hr)) return hr;
    return SonixAsicWrite(ks, nodeId, addr, static_cast<BYTE>(value & mask));
}

static HRESULT SonixFlashStatusGet(IKsControl *ks, DWORD nodeId, BYTE *data,
                                   ULONG dataLen) {
    if (!data || dataLen != 12) {
        return E_INVALIDARG;
    }
    ZeroMemory(data, dataLen);
    ULONG returned = 0;
    return KsProperty(ks, PROPSETID_SONIX_SYS_XU, nodeId,
                      SONIX_SYS_FLASH_STATUS_SELECTOR, KSPROPERTY_TYPE_GET,
                      data, dataLen, &returned);
}

static HRESULT SonixFlashStatusWord(IKsControl *ks, DWORD nodeId, WORD *value) {
    BYTE data[12] = {};
    HRESULT hr = SonixFlashStatusGet(ks, nodeId, data, sizeof(data));
    if (FAILED(hr)) return hr;
    *value = static_cast<WORD>(data[4] | (static_cast<WORD>(data[5]) << 8));
    return S_OK;
}

static HRESULT SonixFlashStatusByte2(IKsControl *ks, DWORD nodeId, BYTE *value) {
    BYTE data[12] = {};
    HRESULT hr = SonixFlashStatusGet(ks, nodeId, data, sizeof(data));
    if (FAILED(hr)) return hr;
    *value = data[6];
    return S_OK;
}

static HRESULT SonixFlashWait1084(IKsControl *ks, DWORD nodeId) {
    for (unsigned int i = 0; i < 1000; ++i) {
        BYTE value = 0;
        HRESULT hr = SonixAsicRead(ks, nodeId, 0x1084, &value);
        if (FAILED(hr)) return hr;
        if (value == 1) return S_OK;
        Sleep(1);
    }
    return HRESULT_FROM_WIN32(ERROR_TIMEOUT);
}

static HRESULT SonixFlashWaitReady(IKsControl *ks, DWORD nodeId) {
    for (unsigned int i = 0; i < 10000; ++i) {
        HRESULT hr = SonixAsicWrite(ks, nodeId, 0x1091, 0x00);
        if (FAILED(hr)) return hr;
        hr = SonixAsicWrite(ks, nodeId, 0x1082, 0x05);
        if (FAILED(hr)) return hr;
        hr = SonixAsicWrite(ks, nodeId, 0x1081, 0x01);
        if (FAILED(hr)) return hr;
        hr = SonixFlashWait1084(ks, nodeId);
        if (FAILED(hr)) return hr;
        hr = SonixAsicWrite(ks, nodeId, 0x1083, 0x00);
        if (FAILED(hr)) return hr;
        hr = SonixAsicWrite(ks, nodeId, 0x1081, 0x02);
        if (FAILED(hr)) return hr;
        hr = SonixFlashWait1084(ks, nodeId);
        if (FAILED(hr)) return hr;

        BYTE status = 0;
        hr = SonixAsicRead(ks, nodeId, 0x1083, &status);
        if (FAILED(hr)) return hr;
        if ((status & 0x01) == 0) {
            return SonixAsicWrite(ks, nodeId, 0x1091, 0x01);
        }
        Sleep(1);
    }
    return HRESULT_FROM_WIN32(ERROR_TIMEOUT);
}

static HRESULT SonixDisableFlashWriteProtectDefault(IKsControl *ks, DWORD nodeId,
                                                    BYTE wpParam) {
    WORD statusBase = 0;
    HRESULT hr = SonixFlashStatusWord(ks, nodeId, &statusBase);
    if (FAILED(hr)) return hr;

    BYTE jedec[4] = {};
    unsigned int jedecValue = 0;
    for (unsigned int i = 0; i < 4; ++i) {
        hr = SonixAsicRead(ks, nodeId, statusBase + 0x0F + i, &jedec[i]);
        if (FAILED(hr)) return hr;
        jedecValue |= static_cast<unsigned int>(jedec[i]) << (24 - 8 * i);
    }
    BYTE statusByte = 0;
    hr = SonixFlashStatusByte2(ks, nodeId, &statusByte);
    if (FAILED(hr)) return hr;

    std::wcout << L"Flash status preamble: base=0x" << std::hex << std::uppercase
               << statusBase << L", id=";
    PrintBytes(jedec, 4);
    std::wcout << L"Flash status byte2=0x" << std::hex << std::uppercase
               << std::setw(2) << std::setfill(L'0')
               << static_cast<unsigned int>(statusByte)
               << std::dec << std::setfill(L' ') << L"\n";

    BYTE bitIndex = static_cast<BYTE>((wpParam >> 4) & 0x07);
    BYTE mode = static_cast<BYTE>(wpParam & 0x03);
    if ((wpParam & 0x0C) == 0x08) {
        if (mode == 2) mode = 1;
        if (mode == 3) mode = 2;
    }

    if (mode != 0) {
        if (bitIndex >= 8) {
            return HRESULT_FROM_WIN32(ERROR_NOT_SUPPORTED);
        }
        BYTE mask = static_cast<BYTE>(1u << bitIndex);
        hr = SonixAsicWrite(ks, nodeId, 0x1007, mask);
        if (FAILED(hr)) return hr;
        hr = SonixAsicWrite(ks, nodeId, 0x1006,
                            mode == 1 ? static_cast<BYTE>(~mask) : mask);
        if (FAILED(hr)) return hr;
    }

    hr = SonixAsicWrite(ks, nodeId, 0x1080, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1091, 0x00);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1082, 0x06);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1081, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixFlashWait1084(ks, nodeId);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1091, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixFlashWaitReady(ks, nodeId);
    if (FAILED(hr)) return hr;

    hr = SonixAsicWrite(ks, nodeId, 0x1091, 0x00);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1082, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1081, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixFlashWait1084(ks, nodeId);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1082, 0x00);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1081, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixFlashWait1084(ks, nodeId);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1091, 0x01);
    if (FAILED(hr)) return hr;
    hr = SonixFlashWaitReady(ks, nodeId);
    if (FAILED(hr)) return hr;
    hr = SonixAsicWrite(ks, nodeId, 0x1080, 0x00);
    if (FAILED(hr)) return hr;

    hr = SonixAsicOr(ks, nodeId, 0x1006, 0x04);
    if (FAILED(hr)) return hr;
    hr = SonixAsicOr(ks, nodeId, 0x1007, 0x04);
    if (FAILED(hr)) return hr;
    hr = SonixAsicOr(ks, nodeId, 0x17C1, 0x01);
    if (FAILED(hr)) return hr;
    return SonixAsicOr(ks, nodeId, 0x17C2, 0x01);
}

static HRESULT SonixEnableFlashWriteProtectDefault(IKsControl *ks, DWORD nodeId) {
    return SonixAsicAnd(ks, nodeId, 0x1073, 0xFE);
}

int wmain(int argc, wchar_t **argv) {
    bool doSet = false;
    bool doSfRead = false;
    bool doSfPatchFromCandidate = false;
    bool doAltSfRead = false;
    bool doAsicRead = false;
    bool doAsicReadBin = false;
    bool doAsicWrite = false;
    bool acceptBrickRisk = false;
    bool unlockWriteProtect = false;
    BYTE setLine = 0;
    BYTE setBlock = 0;
    unsigned int sfAddr = 0;
    unsigned int sfLen = 0;
    std::wstring sfOutPath;
    std::wstring expectedDumpPath;
    std::wstring candidateDumpPath;
    unsigned int asicAddr = 0;
    unsigned int asicLen = 0;
    std::wstring asicOutPath;
    BYTE asicWriteValue = 0;

    if (argc == 4 && std::wstring(argv[1]) == L"--set") {
        doSet = true;
        setLine = static_cast<BYTE>(wcstoul(argv[2], nullptr, 0));
        setBlock = static_cast<BYTE>(wcstoul(argv[3], nullptr, 0));
    } else if (argc == 5 && std::wstring(argv[1]) == L"--sf-read") {
        doSfRead = true;
        sfAddr = static_cast<unsigned int>(wcstoul(argv[2], nullptr, 0));
        sfLen = static_cast<unsigned int>(wcstoul(argv[3], nullptr, 0));
        sfOutPath = argv[4];
        if (sfLen == 0) {
            std::wcerr << L"sf-read length must be > 0\n";
            return 2;
        }
    } else if (argc >= 4 &&
               std::wstring(argv[1]) == L"--sf-patch-from-candidate") {
        doSfPatchFromCandidate = true;
        expectedDumpPath = argv[2];
        candidateDumpPath = argv[3];
        for (int i = 4; i < argc; ++i) {
            std::wstring flag = argv[i];
            if (flag == L"--i-accept-brick-risk") {
                acceptBrickRisk = true;
            } else if (flag == L"--unlock-write-protect") {
                unlockWriteProtect = true;
            } else {
                std::wcerr << L"unknown flag for sf-patch-from-candidate: " << flag << L"\n";
                return 2;
            }
        }
    } else if (argc == 5 && std::wstring(argv[1]) == L"--alt-sf-read") {
        doAltSfRead = true;
        sfAddr = static_cast<unsigned int>(wcstoul(argv[2], nullptr, 0));
        sfLen = static_cast<unsigned int>(wcstoul(argv[3], nullptr, 0));
        sfOutPath = argv[4];
        if (sfLen == 0) {
            std::wcerr << L"alt-sf-read length must be > 0\n";
            return 2;
        }
    } else if (argc == 4 && std::wstring(argv[1]) == L"--asic-read") {
        doAsicRead = true;
        asicAddr = static_cast<unsigned int>(wcstoul(argv[2], nullptr, 0));
        asicLen = static_cast<unsigned int>(wcstoul(argv[3], nullptr, 0));
        if (asicLen == 0) {
            std::wcerr << L"asic-read length must be > 0\n";
            return 2;
        }
    } else if (argc == 5 && std::wstring(argv[1]) == L"--asic-read-bin") {
        doAsicReadBin = true;
        asicAddr = static_cast<unsigned int>(wcstoul(argv[2], nullptr, 0));
        asicLen = static_cast<unsigned int>(wcstoul(argv[3], nullptr, 0));
        asicOutPath = argv[4];
        if (asicLen == 0) {
            std::wcerr << L"asic-read-bin length must be > 0\n";
            return 2;
        }
    } else if (argc == 4 && std::wstring(argv[1]) == L"--asic-write") {
        doAsicWrite = true;
        asicAddr = static_cast<unsigned int>(wcstoul(argv[2], nullptr, 0));
        asicWriteValue = static_cast<BYTE>(wcstoul(argv[3], nullptr, 0));
    } else if (argc != 1) {
        std::wcerr << L"Usage:\n"
                   << L"  windows_xu_osd_probe.exe\n"
                   << L"  windows_xu_osd_probe.exe --set 0 0\n"
                   << L"  windows_xu_osd_probe.exe --sf-read 0x0 0x20000 out\\current_device_dump.bin\n"
                   << L"  windows_xu_osd_probe.exe --sf-patch-from-candidate out\\current.bin out\\candidate.bin [--i-accept-brick-risk] [--unlock-write-protect]\n"
                   << L"  windows_xu_osd_probe.exe --alt-sf-read 0x0 0x10 out\\alt_probe.bin\n"
                   << L"  windows_xu_osd_probe.exe --asic-read 0x0E20 0x20\n"
                   << L"  windows_xu_osd_probe.exe --asic-read-bin 0x0E00 0x100 out\\xdata_0e00.bin\n"
                   << L"  windows_xu_osd_probe.exe --asic-write 0x0E37 0x05\n";
        return 2;
    }

    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(hr)) {
        std::wcerr << L"CoInitializeEx failed: " << HresultText(hr) << L"\n";
        return 1;
    }

    IBaseFilter *filter = nullptr;
    IKsTopologyInfo *topo = nullptr;
    IKsControl *ks = nullptr;
    std::wstring name;
    std::wstring path;

    hr = FindSonixCamera(&filter, &name, &path);
    if (FAILED(hr)) {
        std::wcerr << L"Target camera not found: " << HresultText(hr) << L"\n";
        CoUninitialize();
        return 1;
    }

    std::wcout << L"Camera: " << name << L"\n";
    std::wcout << L"Path:   " << path << L"\n";

    hr = filter->QueryInterface(IID_PPV_ARGS(&topo));
    if (FAILED(hr)) {
        std::wcerr << L"IKsTopologyInfo not available: " << HresultText(hr) << L"\n";
        SafeRelease(&filter);
        CoUninitialize();
        return 1;
    }

    hr = filter->QueryInterface(IID_PPV_ARGS(&ks));
    if (FAILED(hr)) {
        std::wcerr << L"IKsControl not available from filter: " << HresultText(hr) << L"\n";
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 1;
    }

    std::vector<DWORD> devSpecificNodes;
    hr = ListNodes(topo, &devSpecificNodes);
    if (FAILED(hr)) {
        std::wcerr << L"ListNodes failed: " << HresultText(hr) << L"\n";
        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 1;
    }
    if (devSpecificNodes.empty()) {
        std::wcerr << L"No DEV_SPECIFIC KS node found; usbvideo.sys did not expose XU nodes.\n";
        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 1;
    }

    if (doSfRead) {
        DWORD sfNode = 0;
        bool foundSfNode = false;
        std::vector<BYTE> probe;
        for (DWORD candidate : devSpecificNodes) {
            std::wcout << L"Trying SONiX system flash read on DEV_SPECIFIC node "
                       << candidate << L"...\n";
            hr = SonixSfReadRange(ks, candidate, sfAddr, min(8u, sfLen), &probe);
            if (SUCCEEDED(hr)) {
                sfNode = candidate;
                foundSfNode = true;
                std::wcout << L"  probe bytes: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
                break;
            }
            std::wcout << L"  failed: " << HresultText(hr) << L"\n";
        }

        if (!foundSfNode) {
            std::wcerr << L"SF read failed on all DEV_SPECIFIC nodes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::wcout << L"Using SONiX system XU node: " << sfNode << L"\n";
        std::vector<BYTE> flash;
        hr = SonixSfReadRange(ks, sfNode, sfAddr, sfLen, &flash);
        if (FAILED(hr)) {
            std::wcerr << L"SF read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::ofstream out(sfOutPath, std::ios::binary);
        if (!out) {
            std::wcerr << L"Cannot open output file: " << sfOutPath << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        out.write(reinterpret_cast<const char *>(flash.data()),
                  static_cast<std::streamsize>(flash.size()));
        out.close();
        std::wcout << L"Wrote " << flash.size() << L" bytes to " << sfOutPath << L"\n";

        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    if (doSfPatchFromCandidate) {
        std::vector<BYTE> expected;
        std::vector<BYTE> candidate;
        std::wstring error;
        if (!LoadBinaryFile(expectedDumpPath, &expected, &error)) {
            std::wcerr << L"Cannot read expected dump: " << expectedDumpPath
                       << L" (" << error << L")\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        if (!LoadBinaryFile(candidateDumpPath, &candidate, &error)) {
            std::wcerr << L"Cannot read candidate dump: " << candidateDumpPath
                       << L" (" << error << L")\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        if (expected.empty() || expected.size() != candidate.size()) {
            std::wcerr << L"Expected and candidate dumps must be same non-zero size.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        if (expected.size() > 0x20000u) {
            std::wcerr << L"Refusing patch: dump size is larger than expected 0x20000 bytes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::vector<unsigned int> diffs;
        for (size_t i = 0; i < expected.size(); ++i) {
            if (expected[i] == candidate[i]) continue;
            if ((expected[i] & candidate[i]) != candidate[i]) {
                std::wcerr << L"Refusing patch: byte at 0x" << std::hex
                           << std::uppercase << i << std::dec
                           << L" would require 0->1 flash transition.\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }
            diffs.push_back(static_cast<unsigned int>(i));
        }

        if (diffs.empty()) {
            std::wcout << L"Candidate has no differences from expected dump.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 0;
        }
        if (diffs.size() > 8) {
            std::wcerr << L"Refusing patch: more than one 8-byte write block would change ("
                       << diffs.size() << L" bytes differ).\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        unsigned int blockAddr = diffs[0] & ~0x7u;
        for (unsigned int diff : diffs) {
            if ((diff & ~0x7u) != blockAddr) {
                std::wcerr << L"Refusing patch: diffs span multiple 8-byte write blocks.\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }
        }
        if (blockAddr + 8 > expected.size()) {
            std::wcerr << L"Refusing patch: computed write block exceeds dump size.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::wcout << L"Patch plan: one 8-byte flash program block at 0x"
                   << std::hex << std::uppercase << blockAddr << std::dec << L"\n";
        for (unsigned int diff : diffs) {
            std::wcout << L"  diff 0x" << std::hex << std::uppercase << diff
                       << L": 0x" << std::setw(2) << std::setfill(L'0')
                       << static_cast<unsigned int>(expected[diff])
                       << L" -> 0x" << std::setw(2)
                       << static_cast<unsigned int>(candidate[diff])
                       << std::dec << std::setfill(L' ') << L"\n";
        }

        DWORD sfNode = 0;
        bool foundSfNode = false;
        std::vector<BYTE> probe;
        for (DWORD candidateNode : devSpecificNodes) {
            std::wcout << L"Trying SONiX system flash read on DEV_SPECIFIC node "
                       << candidateNode << L"...\n";
            hr = SonixSfReadRange(ks, candidateNode, 0, 8, &probe);
            if (SUCCEEDED(hr) && BytesEqual(probe.data(), expected.data(), 8)) {
                sfNode = candidateNode;
                foundSfNode = true;
                std::wcout << L"  header matches expected dump: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
                break;
            }
            if (SUCCEEDED(hr)) {
                std::wcout << L"  header mismatch: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
            } else {
                std::wcout << L"  failed: " << HresultText(hr) << L"\n";
            }
        }

        if (!foundSfNode) {
            std::wcerr << L"SF read did not find a node whose header matches expected dump.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::vector<BYTE> currentBlock;
        hr = SonixSfReadRange(ks, sfNode, blockAddr, 8, &currentBlock);
        if (FAILED(hr)) {
            std::wcerr << L"Pre-write block read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        const BYTE *expectedBlock = expected.data() + blockAddr;
        const BYTE *candidateBlock = candidate.data() + blockAddr;
        std::wcout << L"Current block:  ";
        PrintBytes(currentBlock.data(), static_cast<ULONG>(currentBlock.size()));
        std::wcout << L"Expected block: ";
        PrintBytes(expectedBlock, 8);
        std::wcout << L"Target block:   ";
        PrintBytes(candidateBlock, 8);

        if (BytesEqual(currentBlock.data(), candidateBlock, 8)) {
            std::wcout << L"Device already matches target block. No write needed.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 0;
        }
        if (!BytesEqual(currentBlock.data(), expectedBlock, 8)) {
            std::wcerr << L"Refusing patch: device block no longer matches expected dump.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        if (!acceptBrickRisk) {
            std::wcout << L"Dry run only. Add --i-accept-brick-risk to program this block.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 0;
        }

        bool writeProtectUnlocked = false;
        if (unlockWriteProtect) {
            BYTE chipId = 0;
            hr = SonixAsicRead(ks, sfNode, 0x101F, &chipId);
            if (FAILED(hr)) {
                std::wcerr << L"Cannot read chip id at ASIC 0x101F: " << HresultText(hr) << L"\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }

            unsigned int wpAddr = 0x8034;
            if (chipId == 0x33) {
                wpAddr = 0x000F;
            } else if (chipId == 0x32 || chipId == 0x76 || chipId == 0x75) {
                wpAddr = 0xC034;
            } else if (chipId == 0x16) {
                wpAddr = 0x5834;
            }
            if (wpAddr >= expected.size()) {
                std::wcerr << L"Write-protect parameter address exceeds dump size.\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }

            BYTE wpParam = expected[wpAddr];
            std::wcout << L"Unlocking flash write protect: chipId=0x"
                       << std::hex << std::uppercase << std::setw(2)
                       << std::setfill(L'0') << static_cast<unsigned int>(chipId)
                       << L", wpParam[0x" << wpAddr << L"]=0x"
                       << std::setw(2) << static_cast<unsigned int>(wpParam)
                       << std::dec << std::setfill(L' ') << L"\n";
            hr = SonixDisableFlashWriteProtectDefault(ks, sfNode, wpParam);
            if (FAILED(hr)) {
                std::wcerr << L"Disable flash write protect failed: " << HresultText(hr) << L"\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }
            writeProtectUnlocked = true;
        }

        std::wcout << L"Programming target block through SONiX selector 0x03...\n";
        hr = SonixSfWrite8(ks, sfNode, blockAddr, candidateBlock);
        if (FAILED(hr)) {
            std::wcerr << L"SF write failed: " << HresultText(hr) << L"\n";
            if (writeProtectUnlocked) {
                HRESULT relockHr = SonixEnableFlashWriteProtectDefault(ks, sfNode);
                std::wcout << L"Relock after write failure: " << HresultText(relockHr) << L"\n";
            }
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        Sleep(100);
        std::vector<BYTE> verifyBlock;
        hr = SonixSfReadRange(ks, sfNode, blockAddr, 8, &verifyBlock);
        if (FAILED(hr)) {
            std::wcerr << L"Post-write block read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        std::wcout << L"Verify block:   ";
        PrintBytes(verifyBlock.data(), static_cast<ULONG>(verifyBlock.size()));
        if (!BytesEqual(verifyBlock.data(), candidateBlock, 8)) {
            std::wcerr << L"Post-write verification failed: target block did not stick.\n";
            if (writeProtectUnlocked) {
                HRESULT relockHr = SonixEnableFlashWriteProtectDefault(ks, sfNode);
                std::wcout << L"Relock after verify failure: " << HresultText(relockHr) << L"\n";
            }
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        if (writeProtectUnlocked) {
            HRESULT relockHr = SonixEnableFlashWriteProtectDefault(ks, sfNode);
            if (FAILED(relockHr)) {
                std::wcerr << L"Post-write relock failed: " << HresultText(relockHr) << L"\n";
                SafeRelease(&ks);
                SafeRelease(&topo);
                SafeRelease(&filter);
                CoUninitialize();
                return 1;
            }
            std::wcout << L"Post-write relock passed.\n";
        }

        std::wcout << L"Post-write verification passed.\n";
        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    if (doAltSfRead) {
        DWORD sfNode = 0;
        bool foundSfNode = false;
        std::vector<BYTE> probe;
        for (DWORD candidate : devSpecificNodes) {
            std::wcout << L"Trying SONiX alternate SPI read on DEV_SPECIFIC node "
                       << candidate << L"...\n";
            hr = SonixAltSfReadRange(ks, candidate, sfAddr, min(8u, sfLen), &probe);
            if (SUCCEEDED(hr)) {
                sfNode = candidate;
                foundSfNode = true;
                std::wcout << L"  probe bytes: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
                break;
            }
            std::wcout << L"  failed: " << HresultText(hr) << L"\n";
        }

        if (!foundSfNode) {
            std::wcerr << L"Alternate SPI read failed on all DEV_SPECIFIC nodes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::wcout << L"Using SONiX system XU node: " << sfNode << L"\n";
        std::vector<BYTE> flash;
        hr = SonixAltSfReadRange(ks, sfNode, sfAddr, sfLen, &flash);
        if (FAILED(hr)) {
            std::wcerr << L"Alternate SPI read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::ofstream out(sfOutPath, std::ios::binary);
        if (!out) {
            std::wcerr << L"Cannot open output file: " << sfOutPath << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        out.write(reinterpret_cast<const char *>(flash.data()),
                  static_cast<std::streamsize>(flash.size()));
        out.close();
        std::wcout << L"Wrote " << flash.size() << L" bytes to " << sfOutPath << L"\n";

        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    if (doAsicRead) {
        DWORD asicNode = 0;
        bool foundAsicNode = false;
        std::vector<BYTE> probe;
        for (DWORD candidate : devSpecificNodes) {
            std::wcout << L"Trying SONiX system ASIC read on DEV_SPECIFIC node "
                       << candidate << L"...\n";
            hr = SonixAsicReadRange(ks, candidate, asicAddr, min(4u, asicLen), &probe);
            if (SUCCEEDED(hr)) {
                asicNode = candidate;
                foundAsicNode = true;
                std::wcout << L"  probe bytes: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
                break;
            }
            std::wcout << L"  failed: " << HresultText(hr) << L"\n";
        }

        if (!foundAsicNode) {
            std::wcerr << L"ASIC read failed on all DEV_SPECIFIC nodes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::vector<BYTE> values;
        hr = SonixAsicReadRange(ks, asicNode, asicAddr, asicLen, &values);
        if (FAILED(hr)) {
            std::wcerr << L"ASIC read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::wcout << L"Using SONiX system XU node: " << asicNode << L"\n";
        for (unsigned int row = 0; row < asicLen; row += 16) {
            unsigned int thisLen = min(16u, asicLen - row);
            std::wcout << L"0x" << std::hex << std::uppercase
                       << std::setw(4) << std::setfill(L'0') << (asicAddr + row)
                       << std::dec << std::setfill(L' ') << L": ";
            PrintBytes(values.data() + row, thisLen);
        }

        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    if (doAsicReadBin) {
        DWORD asicNode = 0;
        bool foundAsicNode = false;
        std::vector<BYTE> probe;
        for (DWORD candidate : devSpecificNodes) {
            std::wcout << L"Trying SONiX system ASIC binary read on DEV_SPECIFIC node "
                       << candidate << L"...\n";
            hr = SonixAsicReadRange(ks, candidate, asicAddr, min(4u, asicLen), &probe);
            if (SUCCEEDED(hr)) {
                asicNode = candidate;
                foundAsicNode = true;
                std::wcout << L"  probe bytes: ";
                PrintBytes(probe.data(), static_cast<ULONG>(probe.size()));
                break;
            }
            std::wcout << L"  failed: " << HresultText(hr) << L"\n";
        }

        if (!foundAsicNode) {
            std::wcerr << L"ASIC binary read failed on all DEV_SPECIFIC nodes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::vector<BYTE> values;
        hr = SonixAsicReadRange(ks, asicNode, asicAddr, asicLen, &values);
        if (FAILED(hr)) {
            std::wcerr << L"ASIC binary read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::ofstream out(asicOutPath, std::ios::binary);
        if (!out) {
            std::wcerr << L"Cannot open ASIC binary output file: " << asicOutPath << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        out.write(reinterpret_cast<const char *>(values.data()),
                  static_cast<std::streamsize>(values.size()));
        out.close();
        std::wcout << L"Using SONiX system XU node: " << asicNode << L"\n";
        std::wcout << L"Wrote " << values.size() << L" ASIC bytes to " << asicOutPath << L"\n";

        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    if (doAsicWrite) {
        DWORD asicNode = 0;
        bool foundAsicNode = false;
        BYTE before = 0;
        for (DWORD candidate : devSpecificNodes) {
            std::wcout << L"Trying SONiX system ASIC write on DEV_SPECIFIC node "
                       << candidate << L"...\n";
            hr = SonixAsicRead(ks, candidate, asicAddr, &before);
            if (SUCCEEDED(hr)) {
                asicNode = candidate;
                foundAsicNode = true;
                std::wcout << L"  current byte: ";
                PrintBytes(&before, 1);
                break;
            }
            std::wcout << L"  failed: " << HresultText(hr) << L"\n";
        }

        if (!foundAsicNode) {
            std::wcerr << L"ASIC write probe failed on all DEV_SPECIFIC nodes.\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        hr = SonixAsicWrite(ks, asicNode, asicAddr, asicWriteValue);
        if (FAILED(hr)) {
            std::wcerr << L"ASIC write failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        BYTE after = 0;
        hr = SonixAsicRead(ks, asicNode, asicAddr, &after);
        if (FAILED(hr)) {
            std::wcerr << L"ASIC verify read failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        std::wcout << L"Using SONiX system XU node: " << asicNode << L"\n";
        std::wcout << L"ASIC 0x" << std::hex << std::uppercase
                   << std::setw(4) << std::setfill(L'0') << asicAddr
                   << L": 0x" << std::setw(2) << static_cast<unsigned int>(before)
                   << L" -> 0x" << std::setw(2) << static_cast<unsigned int>(after)
                   << std::dec << std::setfill(L' ') << L"\n";

        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 0;
    }

    BYTE line = 0;
    BYTE block = 0;
    DWORD usrNode = 0;
    bool foundWorkingNode = false;
    for (DWORD candidate : devSpecificNodes) {
        std::wcout << L"Trying SONiX user OSD GET on DEV_SPECIFIC node "
                   << candidate << L"...\n";
        hr = SonixOsdGet(ks, candidate, &line, &block);
        if (SUCCEEDED(hr)) {
            usrNode = candidate;
            foundWorkingNode = true;
            break;
        }
        std::wcout << L"  failed: " << HresultText(hr) << L"\n";
    }

    if (!foundWorkingNode) {
        std::wcerr << L"OSD GET failed on all DEV_SPECIFIC nodes.\n";
        SafeRelease(&ks);
        SafeRelease(&topo);
        SafeRelease(&filter);
        CoUninitialize();
        return 1;
    }

    std::wcout << L"Using SONiX user XU node: " << usrNode << L"\n";
    std::wcout << L"OSD Enable Line = " << static_cast<unsigned int>(line) << L"\n";
    std::wcout << L"OSD Enable Block = " << static_cast<unsigned int>(block) << L"\n";

    if (doSet) {
        std::wcout << L"Setting OSD Enable Line=" << static_cast<unsigned int>(setLine)
                   << L", Block=" << static_cast<unsigned int>(setBlock) << L"\n";
        hr = SonixOsdSet(ks, usrNode, setLine, setBlock);
        if (FAILED(hr)) {
            std::wcerr << L"OSD SET failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }

        hr = SonixOsdGet(ks, usrNode, &line, &block);
        if (FAILED(hr)) {
            std::wcerr << L"OSD GET after SET failed: " << HresultText(hr) << L"\n";
            SafeRelease(&ks);
            SafeRelease(&topo);
            SafeRelease(&filter);
            CoUninitialize();
            return 1;
        }
        std::wcout << L"After SET: OSD Enable Line = " << static_cast<unsigned int>(line)
                   << L"\n";
        std::wcout << L"After SET: OSD Enable Block = " << static_cast<unsigned int>(block)
                   << L"\n";
    }

    SafeRelease(&ks);
    SafeRelease(&topo);
    SafeRelease(&filter);
    CoUninitialize();
    return 0;
}
