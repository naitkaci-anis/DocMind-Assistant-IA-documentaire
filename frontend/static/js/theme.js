/* theme.js — DocMind Theme Manager
 * La partie anti-flash (inline dans <head>) lit localStorage et pose data-theme
 * avant que le navigateur ne rende quoi que ce soit.
 * Ce fichier gère le toggle et l'état en cours de session.
 */
(function () {
    'use strict';

    /* Bascule entre dark et light */
    window.toggleTheme = function () {
        var html = document.documentElement;
        var curr = html.getAttribute('data-theme') || 'dark';
        var next = curr === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        try { localStorage.setItem('docmind-theme', next); } catch (e) {}
        /* Laisse stars.js ajuster son opacité si la fonction est exposée */
        if (typeof window.setStarsTheme === 'function') window.setStarsTheme(next);
    };
})();
