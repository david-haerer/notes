async function load() {
  const res = await fetch("/static/data.json");
  const notes = await res.json();
  return notes.reverse();
}

function createCard(note) {
  const card = document.createElement("div");
  const header = document.createElement("h2");
  const body = document.createElement("p");
  const links = document.createElement("div");
  const references = document.createElement("div");
  const referencesSummary = document.createElement("h3");
  const mentions = document.createElement("div");
  const mentionsSummary = document.createElement("h3");
  const date = new Date(note.timestamp * 1000);
  card.id = note.timestamp;
  card.className = "card";
  header.innerHTML = `${date
    .toISOString()
    .slice(
      0,
      10
    )} ${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`;
  body.innerHTML = note.content;
  card.appendChild(header);
  card.appendChild(body);
  
  referencesSummary.innerHTML = "References";
  mentionsSummary.innerHTML = "Mentions";
  references.appendChild(referencesSummary);
  mentions.appendChild(mentionsSummary);
  links.className = "links";
  links.appendChild(references);
  links.appendChild(mentions);
  card.appendChild(links);

  return card;
}

async function populate() {
  const notes = await load();
  const main = document.getElementById("main");
  const elems = notes.map((note) => {
    const card = createCard(note);
    main.appendChild(card);
  });
}

populate();


function showModal() {
  document.getElementById("dialog").showModal();
}


const outputBox = document.querySelector("output");
const selectEl = favDialog.querySelector("select");
const confirmBtn = favDialog.querySelector("#confirmBtn");

// "Favorite animal" input sets the value of the submit button
selectEl.addEventListener("change", (e) => {
  confirmBtn.value = selectEl.value;
});

// "Cancel" button closes the dialog without submitting because of [formmethod="dialog"], triggering a close event.
favDialog.addEventListener("close", (e) => {
  outputBox.value =
    favDialog.returnValue === "default"
      ? "No return value."
      : `ReturnValue: ${favDialog.returnValue}.`; // Have to check for "default" rather than empty string
});

// Prevent the "confirm" button from the default behavior of submitting the form, and close the dialog with the `close()` method, which triggers the "close" event.
confirmBtn.addEventListener("click", (event) => {
  event.preventDefault(); // We don't want to submit this fake form
  favDialog.close(selectEl.value); // Have to send the select box value here.
});
