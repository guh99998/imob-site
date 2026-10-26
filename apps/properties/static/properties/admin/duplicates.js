// Cadastro de imóvel: avisa de possíveis duplicados enquanto o formulário é preenchido.
function setupDuplicates() {
  var panel = document.getElementById("duplicates-panel");
  if (!panel) return;
  var form = panel.closest("form") || document.querySelector("form#property_form");
  if (!form) return;
  var names = ["zip_code", "number", "complement", "neighborhood", "category", "bedrooms",
    "area_total", "sale_price", "rent_price"];
  var timer = null;
  var confirmed = [];

  function field(name) { return form.querySelector('[name="' + name + '"]'); }
  function hidden() {
    var input = field("not_duplicate");
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = "not_duplicate";
      form.appendChild(input);
    }
    return input;
  }

  function check() {
    var data = new FormData();
    names.forEach(function (n) { var el = field(n); if (el) data.append(n, el.value); });
    var token = form.querySelector("[name=csrfmiddlewaretoken]");
    fetch(panel.dataset.checkUrl, {
      method: "POST", body: data, credentials: "same-origin",
      headers: { "X-CSRFToken": token ? token.value : "" }
    }).then(function (r) { return r.status === 200 ? r.text() : ""; }).then(function (html) {
      panel.innerHTML = html;
      var btn = panel.querySelector("[data-not-duplicate]");
      if (!btn) return;
      var ids = Array.prototype.map.call(panel.querySelectorAll("[data-duplicate-id]"),
        function (li) { return li.dataset.duplicateId; });
      if (ids.every(function (id) { return confirmed.indexOf(id) !== -1; })) { panel.innerHTML = ""; return; }
      btn.addEventListener("click", function () {
        confirmed = confirmed.concat(ids);
        hidden().value = confirmed.join(",");
        panel.innerHTML = "";
      });
    }).catch(function () { panel.innerHTML = ""; });
  }

  function schedule() { clearTimeout(timer); timer = setTimeout(check, 600); }
  names.forEach(function (n) {
    var el = field(n);
    if (el) { el.addEventListener("input", schedule); el.addEventListener("change", schedule); }
  });
}

// O script vem no <head>: espera o formulário existir.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupDuplicates);
} else {
  setupDuplicates();
}
