export function validateEmail(emailInput, emailError) {
    const email = emailInput.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email)) {
        emailError.textContent = "Please enter a valid email address.";
        return false;
    } else if (email.length > 65) {
        emailError.textContent = "Email address is too long.";
        return false;
    } else {
        emailError.textContent = "";
        return true;
    }
}

export function validatePassword(passwordInput, passwordError) {
    const password = passwordInput.value;

    if (password.length < 5) {
        passwordError.textContent = "Password must be at least 5 characters.";
        passwordInput.value = "";
        return false;
    } else if (password.length > 30) {
        passwordError.textContent = "Password must be 30 characters or less.";
        passwordInput.value = "";
        return false;
    } else if (!/[a-zA-Z]/.test(password)) {
        passwordError.textContent = "Password must contain at least one letter.";
        passwordInput.value = "";
        return false;
    } else if (!/\d/.test(password)) {
        passwordError.textContent = "Password must contain at least one digit.";
        passwordInput.value = "";
        return false;
    } else {
        passwordError.textContent = "";
        return true;
    }
}

export function handleSubmit(form, submitError, flags, url, onSuccess, onFieldError) {
    if (flags.every(flag => flag === true)) {
        submitError.textContent = "";
        const data = {
            email: form.querySelector("#email").value,
            password: form.querySelector("#password").value,
            confirm_password: form.querySelector("#confirm-password")?.value || null,
            username: form.querySelector("#username")?.value || null
        };
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                onSuccess(data.redirect_url);
            } else if (data.status === "error") {
                if (data.field) {
                    onFieldError(data.field, data.message);
                } else {
                    submitError.textContent = data.message;
                }
            }
        })
        .catch(error => {
            submitError.textContent = "An error occurred while submitting data.";
            console.error(error);
        });
    } else {
        submitError.textContent = "Please fill in all required fields.";
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            const trimmed = cookie.trim();
            if (trimmed.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(trimmed.slice(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
