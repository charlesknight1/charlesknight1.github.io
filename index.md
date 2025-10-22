---
layout: page
---

I'm a DPhil candidate in the University of Oxford's School of Geography and the Environment. y research explores the dynamics of the Southern African summer monsoon onset, with a focus on a particular feature called the Congo Air Boundary.

Here you can find my [publications](https://charlesknight1.github.io/publications/), [projects](https://charlesknight1.github.io/projects/) and [fieldwork](https://charlesknight1.github.io/fieldwork/) blogs.

___

<div id="carousel">
  <img id="carouselImage" src="/assets/drycab/20220924_174005-01.jpeg" alt="Image 1">
  <p id="carouselCaption">Caption 1</p>
</div>

<script>
var images = [
  {src: "/assets/drycab/20220924_174005-01.jpeg", caption: "<em>Driving north on the Mwinilunga - Ikelenge highway (T5), North-West Province, Zambia.</em>"},
  {src: "/assets/drycab/20221008_174707.jpg", caption: "<em>The team enjoy a deep red sunset over Angola from our camp at the Nchila Wildlife Reserve, North-West Zambia.<em>"},
  {src: "/assets/drycab/20221103182154_IMG_9506-01.jpeg", caption: "<em>Deep convective clouds over the Democratic Republic of the Congo are lit by the setting sun.<em>"},
  {src: "/assets/kapex/20240105_193617.jpg", caption: "<em>Camp for the night on a roving radiosonde mission in the Kalahari Desert.<em>"}
];
var currentIndex = Math.floor(Math.random() * images.length);

function showImage() {
  document.getElementById("carouselImage").src = images[currentIndex].src;
  document.getElementById("carouselCaption").innerHTML = images[currentIndex].caption;
}

// Show a random image when the page loads
showImage();
</script>
