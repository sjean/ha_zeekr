Java.perform(function () {
  function now() {
    return new Date().toISOString();
  }

  function safeString(value) {
    try {
      if (value === null || value === undefined) {
        return "";
      }
      return String(value);
    } catch (e) {
      return "<error:" + e + ">";
    }
  }

  function readRequestBody(requestBody) {
    if (!requestBody) {
      return "";
    }

    try {
      var Buffer = Java.use("okio.Buffer");
      var buffer = Buffer.$new();
      requestBody.writeTo(buffer);
      return safeString(buffer.readUtf8());
    } catch (e) {
      return "<non-utf8-or-unreadable:" + e + ">";
    }
  }

  function logRequest(tag, request) {
    try {
      var url = safeString(request.url());
      var method = safeString(request.method());
      var headers = safeString(request.headers());
      var body = readRequestBody(request.body());

      console.log("\n===== " + tag + " " + now() + " =====");
      console.log(method + " " + url);
      console.log("--- headers ---");
      console.log(headers);
      if (body) {
        console.log("--- body ---");
        console.log(body);
      }
      console.log("===== /" + tag + " =====\n");
    } catch (e) {
      console.log("[hook-error] " + e);
    }
  }

  var hooked = false;

  try {
    var OkHttpClient = Java.use("okhttp3.OkHttpClient");
    var newCall = OkHttpClient.newCall.overload("okhttp3.Request");
    newCall.implementation = function (request) {
      logRequest("OkHttpClient.newCall", request);
      return newCall.call(this, request);
    };
    hooked = true;
    console.log("[+] Hooked okhttp3.OkHttpClient.newCall");
  } catch (e) {
    console.log("[-] Failed to hook okhttp3.OkHttpClient.newCall: " + e);
  }

  try {
    var RequestBuilder = Java.use("okhttp3.Request$Builder");
    var build = RequestBuilder.build.overload();
    build.implementation = function () {
      var request = build.call(this);
      logRequest("Request.Builder.build", request);
      return request;
    };
    hooked = true;
    console.log("[+] Hooked okhttp3.Request$Builder.build");
  } catch (e) {
    console.log("[-] Failed to hook okhttp3.Request$Builder.build: " + e);
  }

  if (!hooked) {
    console.log("[-] No OkHttp hooks were installed");
  }
});
