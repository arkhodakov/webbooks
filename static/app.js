/**
 * WebBooks - Minimal JavaScript for Cloud Phone
 * Handles reading position storage and keyboard navigation
 */

(function() {
    'use strict';

    var STORAGE_KEY = 'webbooks_positions';

    /**
     * Keyboard navigation for desktop testing
     */
    function setupKeyboardNavigation() {
        document.addEventListener('keydown', function(e) {
            var key = e.key;
            var link = null;

            // Arrow keys and numeric keys for navigation
            if (key === 'ArrowLeft' || key === '4') {
                // Previous page
                link = document.querySelector('a[accesskey="4"]');
            } else if (key === 'ArrowRight' || key === '6') {
                // Next page
                link = document.querySelector('a[accesskey="6"]');
            } else if (key === '5' || key === 'Enter') {
                // Table of contents (center key)
                link = document.querySelector('a[accesskey="5"]');
            } else if (key === 'ArrowUp' || key === 'ArrowDown' || key === '8') {
                // Home / book list
                link = document.querySelector('a[accesskey="8"]');
            }

            if (link) {
                e.preventDefault();
                link.click();
            }
        });
    }

    // Initialize keyboard navigation
    setupKeyboardNavigation();

    /**
     * Save reading position for a book
     * @param {string} bookSlug - Book identifier
     * @param {number} pageNumber - Current page number
     */
    window.savePosition = function(bookSlug, pageNumber) {
        try {
            var positions = loadPositions();
            positions[bookSlug] = {
                page: pageNumber,
                timestamp: Date.now()
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(positions));
        } catch (e) {
            // localStorage may not be available in Cloud Phone
            console.log('Could not save position:', e);
        }
    };

    /**
     * Get saved reading position for a book
     * @param {string} bookSlug - Book identifier
     * @returns {number|null} - Page number or null if not found
     */
    window.getPosition = function(bookSlug) {
        try {
            var positions = loadPositions();
            if (positions[bookSlug]) {
                return positions[bookSlug].page;
            }
        } catch (e) {
            console.log('Could not load position:', e);
        }
        return null;
    };

    /**
     * Load all positions from storage
     * @returns {Object} - Positions object
     */
    function loadPositions() {
        try {
            var data = localStorage.getItem(STORAGE_KEY);
            if (data) {
                return JSON.parse(data);
            }
        } catch (e) {
            console.log('Could not parse positions:', e);
        }
        return {};
    }

    /**
     * Apply saved font size preference
     */
    function applyFontSize() {
        try {
            var fontSize = localStorage.getItem('webbooks_fontsize');
            if (fontSize) {
                document.body.classList.add('font-' + fontSize);
            }
        } catch (e) {
            // Ignore
        }
    }

    /**
     * Set font size preference
     * @param {string} size - 'small', 'medium', or 'large'
     */
    window.setFontSize = function(size) {
        try {
            localStorage.setItem('webbooks_fontsize', size);
            document.body.className = '';
            if (size !== 'medium') {
                document.body.classList.add('font-' + size);
            }
        } catch (e) {
            console.log('Could not save font size:', e);
        }
    };

    // Apply font size on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyFontSize);
    } else {
        applyFontSize();
    }

})();
