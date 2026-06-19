# Birth Form PDF Filler

Android app for filling a fixed government birth registration PDF template and generating a print-ready PDF.

## Features

- Kotlin Android app with Jetpack Compose and Material 3
- MVVM architecture with Hilt dependency injection
- Room database for offline record storage
- Coroutines and StateFlow
- English and Marathi UI labels with instant language switching
- Fixed-coordinate PDF generation using the bundled template
- Embedded Noto Sans Devanagari font for Marathi text
- Save draft, edit, delete, duplicate, and search records
- Generate, preview, save, share, and print generated PDFs
- CSV export for stored records
- Fully offline operation

## PDF Template

The official PDF template is bundled at:

```text
app/src/main/assets/forms/birth_registration_form_v3.pdf
```

PDF coordinates are hardcoded in:

```text
app/src/main/java/com/example/birthformpdf/filler/pdf/PdfCoordinates.kt
```

The template is treated as immutable. There is no coordinate editor or calibration screen.

## Requirements

- Android Studio Ladybug or newer
- JDK 17
- Android SDK Platform 35
- Android SDK Build-Tools 35.0.0 or newer

## Build

Debug APK:

```powershell
.\gradlew.bat :app:assembleDebug
```

Debug output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

Unsigned release APK:

```powershell
.\gradlew.bat :app:assembleRelease
```

Release output:

```text
app/build/outputs/apk/release/app-release-unsigned.apk
```

For a production release, configure Android signing in Android Studio and generate a signed APK.

## Notes

- The app stores generated PDFs inside app storage before save/share/print.
- `Save PDF` uses Android's document picker so the user can choose the destination.
- Printing uses Android's print framework with A4 media and no margins.
- The app does not require internet permission.
