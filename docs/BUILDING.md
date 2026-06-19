# Birth Form PDF Filler - Build Instructions

## Requirements

- Android Studio Ladybug or newer
- JDK 17
- Android SDK Platform 35
- Android SDK Build-Tools 35.0.0 or newer

## Build Debug APK

```powershell
.\gradlew.bat :app:assembleDebug
```

Output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Build Release APK

1. Open the project in Android Studio.
2. Select `Build > Generate Signed App Bundle / APK`.
3. Choose `APK`.
4. Create or select a signing key.
5. Select the `release` variant.

CLI release build after configuring signing:

```powershell
.\gradlew.bat :app:assembleRelease
```

## PDF Template

The immutable template is stored at:

```text
app/src/main/assets/forms/birth_registration_form_v3.pdf
```

Field coordinates are hardcoded in:

```text
app/src/main/java/com/example/birthformpdf/filler/pdf/PdfCoordinates.kt
```

Do not add a coordinate editor or runtime calibration screen. If the official template is replaced, re-render and update these constants once.
