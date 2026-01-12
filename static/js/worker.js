// Web Worker for image loading and processing
// This allows images to be loaded in parallel without blocking the main thread

self.onmessage = function(e) {
    const { type, src, index } = e.data;

    if (type === 'loadImage') {
        // Load image in worker
        fetch(src)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // Create object URL for the image
                const objectUrl = URL.createObjectURL(blob);
                
                // Send back to main thread
                self.postMessage({
                    type: 'imageLoaded',
                    src: objectUrl,
                    index: index,
                    originalSrc: src
                });
            })
            .catch(error => {
                self.postMessage({
                    type: 'imageError',
                    error: error.message,
                    index: index,
                    originalSrc: src
                });
            });
    }
};
