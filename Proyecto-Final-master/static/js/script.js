// // ========== Notificaciones ==========
// window.addEventListener("load", () => {
//   document.querySelectorAll(".message").forEach((msg) => {
//     setTimeout(() => {
//       msg.style.transition = "opacity 0.5s ease-out, transform 0.5s ease-out";
//       msg.style.opacity = "0";
//       msg.style.transform = "translateY(-6px)";
//       setTimeout(() => {
//         msg.style.display = "none";
//       }, 500);
//     }, 3000);
//   });
// });

// // ========== Búsqueda de apartamentos ==========
// const normalizeText = (str) =>
//   str
//     .toLowerCase()
//     .normalize("NFD") // separa acentos
//     .replace(/[\u0300-\u036f]/g, ""); // elimina tildes

// const searchInput = document.getElementById("search-input");
// if (searchInput) {
//   searchInput.addEventListener("input", () => {
//     const value = normalizeText(searchInput.value.trim());
//     const apartmentCards = document.querySelectorAll(".apartamento-card");

//     apartmentCards.forEach((card) => {
//       const title = normalizeText(card.querySelector("h3").textContent);
//       const match = title.includes(value);

//       card.style.transition = "opacity 0.4s ease, transform 0.4s ease";

//       if (match) {
//         // Mostrar
//         card.style.display = "block";
//         requestAnimationFrame(() => {
//           card.style.opacity = "1";
//           card.style.transform = "scale(1)";
//         });
//       } else {
//         // Ocultar con suavidad
//         card.style.opacity = "0";
//         card.style.transform = "scale(0.97)";
//         setTimeout(() => {
//           if (!title.includes(value)) {
//             card.style.display = "none";
//           }
//         }, 400);
//       }
//     });
//   });
// }
