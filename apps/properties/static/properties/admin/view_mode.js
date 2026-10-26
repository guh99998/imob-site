// Página do imóvel: abre só para leitura; "Editar informações" libera os campos.
// Sem JavaScript a página continua editável como antes.
function setupViewMode() {
  var bar = document.getElementById("view-mode-bar");
  var form = document.getElementById("property_form");
  if (!bar || !form) return;

  var button = bar.querySelector("[data-edit-button]");
  var text = bar.querySelector(".pa-viewbar-text");
  var locked = [];
  var startEditing = bar.dataset.startEditing === "1" || /[?&]editar=1/.test(location.search);

  function lockable() {
    // Abas e a própria barra precisam continuar funcionando durante a visualização.
    return Array.prototype.filter.call(
      form.querySelectorAll("input:not([type=hidden]), select, textarea, button"),
      function (el) {
        return !bar.contains(el) && !el.closest("[role=tablist], nav, .tabs") && el.getAttribute("role") !== "tab";
      }
    );
  }

  function lock() {
    document.body.classList.add("pa-viewing");
    lockable().forEach(function (el) {
      if (!el.disabled) {
        el.disabled = true;
        locked.push(el);
      }
    });
    bar.classList.remove("is-editing");
    button.hidden = false;
  }

  function unlock() {
    locked.forEach(function (el) { el.disabled = false; });
    locked = [];
    document.body.classList.remove("pa-viewing");
    bar.classList.add("is-editing");
    button.hidden = true;
    text.innerHTML = "<strong>Editando.</strong> Lembre de salvar ao terminar.";
  }

  button.addEventListener("click", function () {
    unlock();
    var url = location.pathname + (location.search ? location.search + "&" : "?") + "editar=1";
    if (!/[?&]editar=1/.test(location.search)) history.replaceState(null, "", url);
    var first = form.querySelector("input[name=title]");
    if (first) first.focus();
  });

  if (startEditing) {
    bar.classList.add("is-editing");
    button.hidden = true;
    text.innerHTML = "<strong>Editando.</strong> Lembre de salvar ao terminar.";
  } else {
    lock();
  }
}

// O script vem no <head>: espera o formulário existir.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupViewMode);
} else {
  setupViewMode();
}
