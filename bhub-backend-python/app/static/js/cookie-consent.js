// Abre/fecha a central de preferências (<dialog>). Progressive enhancement:
// aceitar/recusar funcionam sem JS (forms HTML); apenas o modal exige JS.
(function () {
  "use strict";
  const dialog = document.getElementById("cookie-preferences");
  if (!dialog || typeof dialog.showModal !== "function") return;

  document.querySelectorAll("[data-consent-open]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      dialog.showModal();
    });
  });

  dialog.querySelectorAll("[data-consent-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      dialog.close();
    });
  });
})();
