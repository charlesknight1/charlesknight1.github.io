---
layout: page
---

I'm a DPhil candidate in the University of Oxford's School of Geography and the Environment. My research focuses on the dynamics and variability of the Southern African summer monsoon onset.

Here you can find my [publications](https://charlesknight1.github.io/publications/), [projects](https://charlesknight1.github.io/projects/) and [fieldwork](https://charlesknight1.github.io/fieldwork/) blogs.

___

![Road in NW Zambia](/assets/20220924_174005-01.jpeg)


*Driving north on the Mwinilunga - Ikelenge highway (T5), North-West Province, Zambia.*

<div id="carousel">
  <img id="carouselImage" src="/assets/20220924_174005-01.jpeg" alt="Image 1">
</div>

<button id="prevButton">Previous</button>
<button id="nextButton">Next</button>

<script>
var images = ["/assets/20220924_174005-01.jpeg", "/assets/20221008_174707.jpg", "/assets/20221028_181128.jpg", "/assets/kapex/20240105_193617.jpg", "/assets/kapex/20240108_191139.jpg"];
var currentIndex = 0;

function showNextImage() {
  currentIndex = (currentIndex < images.length - 1) ? currentIndex + 1 : 0;
  document.getElementById("carouselImage").src = images[currentIndex];
}

document.getElementById("prevButton").addEventListener("click", function() {
  currentIndex = (currentIndex > 0) ? currentIndex - 1 : images.length - 1;
  document.getElementById("carouselImage").src = images[currentIndex];
});

document.getElementById("nextButton").addEventListener("click", showNextImage);

// Automatically advance to the next image every 3 seconds
setInterval(showNextImage, 3000);
</script>
