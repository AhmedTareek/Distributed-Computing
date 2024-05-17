 var filesArray = []; // Array to store selected files

    $(document).ready(function() {

        // When file input changes
        $('#images').on('change', function() {
            var files = $(this)[0].files; // Get the files selected

            // Loop through each file
            for (var i = 0; i < files.length; i++) {
                var reader = new FileReader(); // Create a FileReader object

                // Closure to capture the file information.
                reader.onload = (function(file) {
                    return function(e) {
                        // Render thumbnail preview of the image with delete button
                        $('#uploadedImages').append('<div class="thumbnail">' +
                            '<button class="delete-button" data-file="' + file.name + '">' +

                            '</button>' +
                            '<img src="' + e.target.result + '"   width="auto" height="200px"/>' +
                            '</div>');
                    };
                })(files[i]);

                // Read in the image file as a data URL.
                reader.readAsDataURL(files[i]);

                // Add file to filesArray
                filesArray.push(files[i]);
            }
        });

        // Delete image when delete button is clicked
        $(document).on('click', '.delete-button', function() {
            var fileName = $(this).data('file');
            $(this).parent('.thumbnail').remove(); // Remove the thumbnail div containing the image
            // Remove the corresponding file from filesArray
            filesArray = filesArray.filter(function(file) {
                return file.name !== fileName;
            });
        });

        // Update file input when form is submitted
        $('#uploadForm').on('submit', function() {
            var input = $('#images');
            input.val(''); // Clear the file input
            input[0].files = filesArray; // Update file input with remaining files
        });

    });

     function printImages() {
            console.log("Selected images:");
            console.log( filesArray.length)

     }