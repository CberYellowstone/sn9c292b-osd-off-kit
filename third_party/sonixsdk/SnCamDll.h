
#pragma once
#define DT_API extern "C"

#ifdef SNCAMDLL_EXPORTS
#define SNCAMDLL_API __declspec(dllexport)
#else
#define SNCAMDLL_API __declspec(dllimport)
#endif

// 函数返回值
typedef enum tagDS_CAMERA_STATUS
{
	STATUS_OK = 1,												// 动作成功
	STATUS_INTERNAL_ERROR = 0,							// 内部错误
	STATUS_NO_DEVICE_FIND = -1,							// 没有发现相机
	STATUS_NOT_ENOUGH_SYSTEM_MEMORY = -2,		// 没有足够系统内存
	STATUS_HW_IO_ERROR = -3,								// 硬件IO错误
	STATUS_PARAMETER_INVALID = -4,					// 参数无效
	STATUS_PARAMETER_OUT_OF_BOUND = -5,			// 参数越界
	STATUS_FILE_CREATE_ERROR = -6,						// 创建文件失败
	STATUS_FILE_INVALID = -7,								// 文件格式无效
	STATUS_NO_RESOLUTION_FOUND=-8,					// 不支持此格式
	STATUS_NO_CAM_INIT=-9									// 没有初始化
}DS_CAMERA_STATUS;

// 颜色空间
typedef enum tagDS_COLORSPACE
{
	COLORSPACE_YUY2,											// YUV2
	COLORSPACE_MJPG,											// MJPEG
	COLORSPACE_RGB24,										// RGB24
	COLORSPACE_I420											// I420
}DS_COLORSPACE;

// 录像格式
typedef enum tagDS_VIDEOFORMAT
{
	VIDEOFORMAT_avi,											// AVI
	VIDEOFORMAT_asf											// ASF
}DS_VIDEOFORMAT;

// 拍照格式
typedef enum tagDS_PICTUREFOMAT
{
	PICTUREFORMAT_JPG,										// JPEG
	PICTUREFORMAT_BMP										// BMP
}DS_PICTUREFORMAT;

// 属性项
typedef enum tagDS_CAMERA_PROPERTY
{	
	PROPERTY_Brightness	= 0,								// 亮度
	PROPERTY_Contrast	= 1,									// 对比度
	PROPERTY_Hue	= 2,										// 色调
	PROPERTY_Saturation	= 3,								// 饱和度
	PROPERTY_Sharpness	= 4,								// 清晰度
	PROPERTY_Gamma	= 5,									// 伽马
	PROPERTY_ColorEnable	= 6,								// 黑白
	PROPERTY_WhiteBalance	= 7,							// 白平衡
	PROPERTY_BacklightCompensation	= 8,				// 逆光对比
	PROPERTY_Gain	= 9										// 增益
} DS_CAMERA_PROPERTY;

// 控制项
typedef enum tagDS_CAMERA_CONTROL
{
	CONTROL_Pan	= 0,											// 全景
	CONTROL_Tilt	= 1 ,											// 倾斜
	CONTROL_Roll	= 2 ,											// 镜像翻转
	CONTROL_Zoom	= 3 ,										// 缩放
	CONTROL_Exposure	= 4 ,									// 曝光
	CONTROL_Iris	= 5 ,											// 光圈
	CONTROL_Focus	= 6										// 焦点
} DS_CAMERA_CONTROL;

// 是否自动设置
typedef enum tagDS_PROPERTY_FLAGS
{
	PROPERTY_FLAGS_Auto = 1,								// 自动
	PROPERTY_FLAGS_Manual = 2								// 手动
} DS_PROPERTY_FLAGS, DS_CONTROL_FLAGS;

// 电源频率
typedef enum tagDS_POWER_LINE
{
	POWER_LINE_50Hz = 1,
	POWER_LINE_60Hz = 2
}DS_POWER_LINE;


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	回调函数
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		DS_SNAP_PROC
*	Description:		回调函数（必须定义）
*	Parameters:	每帧预览图像数据，数据长度
*	Return :			被动调用
*/
typedef int (CALLBACK* DS_SNAP_PROC)(BYTE *pImageBuffer, LONG BufferLength);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	设备信息
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		GetCameraCount
*	Description:		获取Camera数量（必须调用）
*	Parameters:	Camera数量
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetCameraCount(OUT LONG* CameraCout);

/*
*	Function:		GetCameraInfo
*	Description:		获取Camera信息
*	Parameters:	相机编号，VID，PID，设备名称
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetCameraInfo(IN BYTE CamNum, 
															OUT CHAR** VID, OUT CHAR** PID,
															OUT CHAR** DeviceName);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	设备初始化与释放
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		CameraInit
*	Description:		初始化Camera（必须调用）
*	Parameters:	相机编号，回调函数，预览窗口句柄（无需预览则NULL）
*	Return :			返回状态
*/

DT_API SNCAMDLL_API DS_CAMERA_STATUS  CameraInit(BYTE CamNum, 
															DS_SNAP_PROC pCallbackFunction,
															HWND hWndDisplay);
/*
*	Function:		CameraUnInit
*	Description:		释放Camera（必须调用）
*	Parameters:	相机编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraUnInit(BYTE CamNum);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	预览
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		GetPreviewResolutionCount
*	Description:		获取Camera支持的预览格式数量
*	Parameters:	相机编号，格式数量
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetPreviewResolutionCount(IN BYTE CamNum, 
															OUT LONG* ResolutionCount);

/*
*	Function:		GetPreviewResolutionInfo
*	Description:		获取相应预览格式信息
*	Parameters:	相机编号，格式编号，色彩空间，宽，高
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetPreviewResolutionInfo(IN BYTE CamNum, 
															IN BYTE ResolutionNum, 
															OUT DS_COLORSPACE* piColorspace,
															OUT LONG* plWidth, 
															OUT LONG* plHeight);

/*
*	Function:		CameraPlay
*	Description:		开始预览
*	Parameters:	相机编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraPlay(BYTE CamNum);

/*
*	Function:		CameraStop
*	Description:		停止预览
*	Parameters:	相机编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraStop(BYTE CamNum);

/*
*	Function:		CameraSetVideoFormat
*	Description:		设置预览格式
*	Parameters:	相机编号，格式编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraSetVideoFormat(BYTE CamNum, 
															BYTE ResolutionNum);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	拍照
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		GetStillResolutionCount
*	Description:		获取Camera支持的拍照格式数量
*	Parameters:	相机编号，格式数量
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetStillResolutionCount(IN BYTE CamNum, 
															OUT LONG* ResolutionCount);
/*
*	Function:		GetStillResolutionInfo
*	Description:		获取相应拍照格式信息
*	Parameters:	相机编号，格式编号，颜色空间，宽，高
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS GetStillResolutionInfo(IN BYTE CamNum, 
															IN BYTE ResolutionNum,
															OUT DS_COLORSPACE* piColorspace,
															OUT LONG* plWidth,
															OUT LONG* plHeight);
/*
*	Function:		CameraSetStillFormat
*	Description:		设置拍照格式
*	Parameters:	相机编号，格式编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraSetStillFormat(BYTE CamNum, 
															BYTE ResolutionNum);
/*
*	Function:		CameraSnapShot
*	Description:		拍照
*	Parameters:	相机编号，BMPorJPEG，图片文件名称（包括图片路径、文件名）
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraSnapShot(BYTE CamNum, 
															DS_PICTUREFORMAT uiformat,
															WCHAR* wszPictureFile
															);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	录像
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		CameraStartCapture
*	Description:		开始录像
*	Parameters:	相机编号，AVIorASF，录像文件名称（包括图片路径、文件名）
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraStartCapture(BYTE CamNum,
															DS_VIDEOFORMAT uiformat,
															WCHAR* wszCaptureFile);
/*
*	Function:		CameraStopCapture
*	Description:		停止录像
*	Parameters:	相机编号
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraStopCapture(BYTE CamNum);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	属性及控制
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		CameraPropertyGetRange
*	Description:		获取属性页项目范围、步进、默认值、是否自动
*	Parameters:	相机编号，属性值，最小值，最大值，步进，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraPropertyGetRange(IN BYTE CamNum, 
															IN DS_CAMERA_PROPERTY uiProperty,
															OUT LONG* pMin, OUT LONG* pMax,
															OUT LONG* pSteppingDelta, 
															OUT LONG* pDefault,
															OUT DS_PROPERTY_FLAGS* pCapsFlags
															);

/*
*	Function:		CameraPropertyGet
*	Description:		获取属性页项目设置值
*	Parameters:	相机编号，属性值，设置值，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraPropertyGet(BYTE CamNum, 
															DS_CAMERA_PROPERTY uiProperty,
															OUT LONG* lValue, 
															OUT DS_PROPERTY_FLAGS* Flags
															);

/*
*	Function:		CameraPropertySet
*	Description:		设置属性页项目
*	Parameters:	相机编号，属性值，设置值，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraPropertySet(BYTE CamNum, 
															DS_CAMERA_PROPERTY uiProperty,
															IN LONG lValue, 
															IN DS_PROPERTY_FLAGS Flags
															);

/*
*	Function:		CameraControlGetRange
*	Description:		获取控制页项目范围、步进、默认值、是否自动
*	Parameters:	相机编号，控制值，最小值，最大值，步进，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraControlGetRange(BYTE CamNum, 
															DS_CAMERA_CONTROL uiControl,
															OUT LONG* pMin, OUT LONG* pMax,
															OUT LONG* pSteppingDelta, 
															OUT LONG* pDefault,
															OUT DS_CONTROL_FLAGS* pCapsFlags
															);

/*
*	Function:		CameraControlGet
*	Description:		获取控制页项目设置值
*	Parameters:	相机编号，控制值，设置值，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraControlGet(BYTE CamNum, 
															DS_CAMERA_CONTROL uiControl,
															OUT LONG* lValue, 
															OUT DS_CONTROL_FLAGS* Flags
															);

/*
*	Function:		CameraControlSet
*	Description:		设置控制页项目
*	Parameters:	相机编号，控制值，设置值，是否自动
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraControlSet(BYTE CamNum, 
															DS_CAMERA_CONTROL uiControl,
															IN LONG lValue, 
															IN DS_CONTROL_FLAGS Flags
															);

/*
*	Function:		CameraGetFrameSpeed
*	Description:		获取当前帧率
*	Parameters:	相机编号，帧率
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraGetFrameSpeed(BYTE CamNum,
															OUT DOUBLE* dFramerate);

/*
*	Function:		CameraSetFrameSpeed
*	Description:		设置帧率
*	Parameters:	相机编号，帧率
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraSetFrameSpeed(BYTE CamNum,
															IN DOUBLE dFramerate);

/*
*	Function:		CameraSetPowerLine
*	Description:		设置电源频率
*	Parameters:	相机编号，电源频率
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraSetPowerLine(BYTE CamNum, 
															IN DS_POWER_LINE PowerLine
															);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//	寄存器
////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/*
*	Function:		CameraReadDSP
*	Description:		读寄存器
*	Parameters:	相机编号，寄存器地址，值
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraReadDSP(BYTE CamNum, 
															LONG laddress, OUT LONG* lData);

/*
*	Function:		CameraWriteDSP
*	Description:		写寄存器
*	Parameters:	相机编号，寄存器地址，值
*	Return :			返回状态
*/
DT_API SNCAMDLL_API DS_CAMERA_STATUS CameraWriteDSP(BYTE CamNum, 
															LONG laddress, IN LONG* lData);