import { $ } from "/static/jquery/src/jquery.js";

function say_hi(elt) {
    console.log("Welcome to", elt.text());
}

say_hi($("h1"));