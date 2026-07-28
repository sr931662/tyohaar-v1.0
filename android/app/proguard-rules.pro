# Flutter's own engine/plugin classes are kept automatically via consumer
# ProGuard rules bundled in the Flutter embedding AAR — no rules needed here
# for Flutter itself.

# --- Razorpay (razorpay_flutter) ---
# Official rules per Razorpay Android SDK docs: reflection-based callbacks
# and webview JS bridge must survive obfuscation/shrinking.
-keep class com.razorpay.** { *; }
-dontwarn com.razorpay.**
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-optimizations !method/inlining/*
-keepattributes *Annotation*

# --- flutter_local_notifications ---
-keep class com.dexterous.** { *; }

# --- image_cropper (uCrop) ---
-keep class com.yalantis.ucrop** { *; }
-dontwarn com.yalantis.ucrop**

# --- Gson (transitively used by several Google/Firebase-adjacent libs for
# reflective (de)serialization; keep generic signatures and type adapters) ---
-keepattributes Signature
-keep class com.google.gson.** { *; }
-keep class * extends com.google.gson.TypeAdapter
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer

# --- Play core / deferred components (referenced by Flutter's embedding for
# split-install support even when unused; silence missing-class warnings) ---
-dontwarn com.google.android.play.core.**
