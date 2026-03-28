/**
 * API клиент: Basic Auth (sessionStorage pi_basic), база из window.__PI_BASE__ (public-config.js).
 */
(function (global) {
  function apiUrl(path) {
    var base = typeof window.__PI_BASE__ === 'string' ? window.__PI_BASE__.replace(/\/$/, '') : '';
    var p = path.startsWith('/') ? path : '/' + path;
    return base + p;
  }

  function getAuthHeader() {
    var t = sessionStorage.getItem('pi_basic');
    if (!t) return null;
    return 'Basic ' + t;
  }

  async function api(path, options) {
    var headers = Object.assign({}, (options && options.headers) || {});
    var auth = getAuthHeader();
    if (!auth) throw new Error('Нет авторизации');
    headers['Authorization'] = auth;
    if (options && options.body && typeof options.body === 'string' && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    var url = apiUrl(path);
    var res = await fetch(url, Object.assign({}, options, { headers: headers }));
    if (res.status === 401) {
      sessionStorage.removeItem('pi_basic');
      throw new Error('401');
    }
    var text = await res.text();
    var data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = text;
    }
    if (!res.ok) {
      var msg =
        data && data.detail
          ? typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail)
          : res.statusText;
      throw new Error(msg || 'Ошибка запроса');
    }
    return data;
  }

  global.PIApi = { api, apiUrl, getAuthHeader };
})(window);
