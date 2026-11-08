/* School Grading Management System - frontend interactivity.
   All validation here is duplicated on the server; JavaScript only
   provides faster feedback and dynamic form handling. */

document.addEventListener("DOMContentLoaded", function () {

    // ------------------------------------------- mobile sidebar toggle
    var menuToggle = document.getElementById("menu-toggle");
    var sidebar = document.getElementById("sidebar");
    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
    }

    // ------------------------------------------- delete confirmation
    document.querySelectorAll("form.delete-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.dataset.confirm || "Delete this record?")) {
                event.preventDefault();
            }
        });
    });

    // ------------------------------------------- student info forms
    var studentForm = document.getElementById("student-form");
    if (studentForm) {
        studentForm.addEventListener("submit", function (event) {
            var errors = [];
            studentForm.querySelectorAll("input[required]").forEach(function (input) {
                input.classList.remove("invalid");
                if (!input.value.trim()) {
                    input.classList.add("invalid");
                    var label = studentForm.querySelector('label[for="' + input.id + '"]');
                    errors.push((label ? label.textContent.replace(" *", "") : input.name) + " is required.");
                }
            });
            var errorBox = document.getElementById("student-form-error");
            if (errors.length) {
                event.preventDefault();
                errorBox.textContent = errors.join("\n");
                errorBox.hidden = false;
            } else {
                errorBox.hidden = true;
            }
        });
    }

    // ------------------------------------------- dynamic marks form
    var marksForm = document.getElementById("marks-form");
    if (marksForm) {
        var maxSubjects = parseInt(marksForm.dataset.maxSubjects, 10) || 8;
        var rowsContainer = document.getElementById("subject-rows");
        var rowTemplate = document.getElementById("subject-row-template");
        var addButton = document.getElementById("add-subject");
        var countLabel = document.getElementById("subject-count");
        var errorBox = document.getElementById("marks-form-error");

        function updateCount() {
            var count = rowsContainer.querySelectorAll(".subject-row").length;
            countLabel.textContent = count + " / " + maxSubjects + " subjects";
            addButton.disabled = count >= maxSubjects;
        }

        function showError(messages) {
            errorBox.textContent = messages.join("\n");
            errorBox.hidden = messages.length === 0;
        }

        addButton.addEventListener("click", function () {
            if (rowsContainer.querySelectorAll(".subject-row").length >= maxSubjects) {
                showError(["A student can take a maximum of " + maxSubjects + " subjects."]);
                return;
            }
            rowsContainer.appendChild(rowTemplate.content.cloneNode(true));
            showError([]);
            updateCount();
        });

        // Event delegation so remove buttons work on newly added rows too.
        rowsContainer.addEventListener("click", function (event) {
            if (event.target.classList.contains("remove-subject")) {
                event.target.closest(".subject-row").remove();
                showError([]);
                updateCount();
            }
        });

        marksForm.addEventListener("submit", function (event) {
            var rows = rowsContainer.querySelectorAll(".subject-row");
            var errors = [];
            var seenNames = {};

            rows.forEach(function (row) {
                var nameInput = row.querySelector('input[name="subject_name"]');
                var marksInput = row.querySelector('input[name="marks"]');
                nameInput.classList.remove("invalid");
                marksInput.classList.remove("invalid");

                var name = nameInput.value.trim();
                var rawMarks = marksInput.value.trim();

                if (!name) {
                    nameInput.classList.add("invalid");
                    errors.push("Subject names cannot be empty.");
                } else if (seenNames[name.toLowerCase()]) {
                    nameInput.classList.add("invalid");
                    errors.push("Duplicate subject name: '" + name + "'.");
                } else {
                    seenNames[name.toLowerCase()] = true;
                }

                var marks = Number(rawMarks);
                if (rawMarks === "" || isNaN(marks)) {
                    marksInput.classList.add("invalid");
                    errors.push("Marks for '" + (name || "subject") + "' must be a number.");
                } else if (marks < 0 || marks > 100) {
                    marksInput.classList.add("invalid");
                    errors.push("Marks for '" + (name || "subject") + "' must be between 0 and 100.");
                }
            });

            if (rows.length === 0) {
                errors.push("Enter at least one subject before submitting results.");
            }
            if (rows.length > maxSubjects) {
                errors.push("A student can take a maximum of " + maxSubjects + " subjects.");
            }

            if (errors.length) {
                event.preventDefault();
                showError(errors);
                errorBox.scrollIntoView({ block: "nearest" });
            }
        });

        updateCount();
    }

    // ------------------------------------------- print results
    var printButton = document.getElementById("print-results");
    if (printButton) {
        printButton.addEventListener("click", function () {
            window.print();
        });
    }
});