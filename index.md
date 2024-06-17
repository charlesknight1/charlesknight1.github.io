---
layout: page
---

I'm a DPhil candidate in the University of Oxford's School of Geography and the Environment. My research focuses on the dynamics and variability of the Southern African summer monsoon onset.

Here you can find my [publications](https://charlesknight1.github.io/publications/), [projects](https://charlesknight1.github.io/projects/) and [fieldwork](https://charlesknight1.github.io/fieldwork/) blogs.

___

<div id="carousel">
  <img id="carouselImage" src="/assets/20220924_174005-01.jpeg" alt="Image 1">
  <p id="carouselCaption">Caption 1</p>
</div>

<button id="prevButton">Previous</button>
<button id="nextButton">Next</button>

<script>
var images = [
  {src: "/assets/20220924_174005-01.jpeg", caption: "<em>Driving north on the Mwinilunga - Ikelenge highway (T5), North-West Province, Zambia.</em>"},
  {src: "/assets/20221008_174707.jpg", caption: "<em>Caption 2.<em>"},
  {src: "/assets/20221103182154_IMG_9506-01.jpeg", caption: "<em>Caption 3.<em>"},
  {src: "/assets/kapex/20240105_193617.jpg", caption: "<em>Caption 4.<em>"}
];
var currentIndex = Math.floor(Math.random() * images.length);

function showImage() {
  document.getElementById("carouselImage").src = images[currentIndex].src;
  document.getElementById("carouselCaption").innerHTML = images[currentIndex].caption;
}

function showNextImage() {
  currentIndex = (currentIndex < images.length - 1) ? currentIndex + 1 : 0;
  showImage();
}

document.getElementById("prevButton").addEventListener("click", function() {
  currentIndex = (currentIndex > 0) ? currentIndex - 1 : images.length - 1;
  showImage();
});

document.getElementById("nextButton").addEventListener("click", showNextImage);

// Automatically advance to the next image every 3 seconds
setInterval(showNextImage, 20000);

// Show a random image when the page loads
showImage();
</script>
