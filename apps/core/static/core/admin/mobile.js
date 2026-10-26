// Admin no celular: copia o título de cada coluna para as células (data-label), usado pelo CSS
// que transforma as linhas da lista em cartões. Sem JS a lista continua rolando na horizontal.
(function () {
  function headerNames(table) {
    return Array.prototype.map.call(table.querySelectorAll("thead th"), function (th) {
      var copy = th.cloneNode(true);
      copy.querySelectorAll(".material-symbols-outlined, svg, input, label").forEach(function (n) {
        n.remove();
      });
      // Número de prioridade da ordenação (ex.: "2") não faz parte do nome da coluna.
      copy.querySelectorAll("span, div").forEach(function (n) {
        if (/^\d+$/.test(n.textContent.trim()) && !n.children.length) n.remove();
      });
      return copy.textContent.replace(/\s+/g, " ").trim();
    });
  }

  function label(table) {
    var names = headerNames(table);
    table.querySelectorAll("tbody tr").forEach(function (row) {
      Array.prototype.forEach.call(row.children, function (cell, i) {
        cell.setAttribute("data-label", names[i] || "");
        var text = cell.textContent.replace(/\s+/g, "").trim();
        var hasControl = cell.querySelector("img, input, a, button, select");
        if ((text === "" || text === "-") && !hasControl) cell.setAttribute("data-empty", "");
      });
    });
  }

  function run() {
    document.querySelectorAll("table.result-list").forEach(label);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
