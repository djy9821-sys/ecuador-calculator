package com.sunolta.hematlistrik;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Locale;

/** Shows the bundled calculator page full screen. Links to other sites open in the phone's browser. */
public class MainActivity extends Activity {
    // Fixed origin so the page keeps its saved numbers; nothing is ever fetched from it.
    private static final String ORIGIN = "https://hemat-listrik.sunolta.local/";
    private static final String XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    // Same colours as the page, so the header and footer run into the system bars.
    private static final int BAR_COLOR = 0xFF3A403D;
    private static final int PAGE_COLOR = 0xFFEEF1ED;

    private WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BAR_COLOR);
        getWindow().setNavigationBarColor(BAR_COLOR);
        web = new WebView(this);
        web.setBackgroundColor(PAGE_COLOR);
        setContentView(web);

        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        // The page scales its own text from Bridge.fontScale, so every WebView version behaves the same.
        settings.setTextZoom(100);

        web.addJavascriptInterface(new Bridge(), "HematAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl()));
                } catch (android.content.ActivityNotFoundException e) {
                    // No browser on the phone: stay on the calculator.
                }
                return true;
            }
        });
        web.loadDataWithBaseURL(ORIGIN, readPage(), "text/html", "utf-8", null);
    }

    @Override
    public void onBackPressed() {
        // The page closes an enlarged photo first; otherwise leave the app as usual.
        web.evaluateJavascript("window.hematBack?hematBack():false", result -> {
            if (!"true".equals(result)) MainActivity.super.onBackPressed();
        });
    }

    private String readPage() {
        try (InputStream in = getAssets().open("index.html")) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[16384];
            for (int n; (n = in.read(buffer)) > 0; ) out.write(buffer, 0, n);
            return out.toString("UTF-8");
        } catch (IOException e) {
            throw new IllegalStateException("index.html is missing from the app", e);
        }
    }

    private boolean isChinese() {
        return "zh".equals(Locale.getDefault().getLanguage());
    }

    /** Called by the small script that build_apk.py adds to the page. */
    private final class Bridge {
        @JavascriptInterface
        public float fontScale() {
            return getResources().getConfiguration().fontScale;
        }

        @JavascriptInterface
        public void copy(String text) {
            ClipboardManager clipboard = getSystemService(ClipboardManager.class);
            clipboard.setPrimaryClip(ClipData.newPlainText("Hemat Listrik Kincir", text));
        }

        @JavascriptInterface
        public boolean save(String filename, String base64) {
            boolean saved = writeDownload(filename, Base64.decode(base64, Base64.DEFAULT));
            final String message = !saved
                    ? (isChinese() ? "保存失败" : "Gagal menyimpan")
                    : (isChinese() ? "已保存到“下载”文件夹" : "Tersimpan di folder Download");
            runOnUiThread(() -> Toast.makeText(MainActivity.this, message, Toast.LENGTH_LONG).show());
            return saved;
        }

        private boolean writeDownload(String filename, byte[] bytes) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.Downloads.DISPLAY_NAME, filename);
                    values.put(MediaStore.Downloads.MIME_TYPE, XLSX_MIME);
                    Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) return false;
                    try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                        out.write(bytes);
                    }
                } else {
                    File file = new File(getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), filename);
                    try (OutputStream out = new FileOutputStream(file)) {
                        out.write(bytes);
                    }
                }
                return true;
            } catch (IOException | RuntimeException e) {
                return false;
            }
        }
    }
}
