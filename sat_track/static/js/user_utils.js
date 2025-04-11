export function validateEmail(emailInput, emailError) {
    const email = emailInput.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email)) {
        emailError.textContent = "podaj poprawny email";
        return false;
    } else if (email.length > 65) {
        emailError.textContent = "e-mail jest za długi";
        return false;
    } else {
        emailError.textContent = "";
        return true;
    }
}


export function validatePassword(passwordInput, passwordError) {
    const password = passwordInput.value;

    if (password.length < 5) {
        passwordError.textContent = "hasło musi mieć przynajmniej 5 znaków";
        passwordInput.value = "";
        return false;
    } else if (password.length > 30) {
        passwordError.textContent = "hasło musi mieć nie więcej niż 30 znaków";
        passwordInput.value = "";
        return false;
    } else if (!/[a-zA-Z]/.test(password)) {
        passwordError.textContent = "hasło musi mieć przynajmniej jedną literę";
        passwordInput.value = "";
        return false;
    } else if (!/\d/.test(password)) {
        passwordError.textContent = "hasło musi mieć przynajmniej jedną cyfrę";
        passwordInput.value = "";
        return false;
    } else {
        passwordError.textContent = "";
        return true;
    }
}

// export function handleSubmit(form, submitError, flags) {
//
//     if (flags.every(flag => flag === true)) {
//         submitError.textContent = "";
//         form.submit();
//     } else {
//         submitError.textContent = "uzupełnij wszystkie dane";
//     }
// }

export function handleSubmit(form, submitError, flags, url, onSuccess, onFieldError) {
    if (flags.every(flag => flag === true)) {
        submitError.textContent = "";

        const data = {
            email: form.querySelector("#email").value,
            password: form.querySelector("#password").value,
            confirm_password: form.querySelector("#confirm-password")?.value || null  // optional

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
            submitError.textContent = "Wystąpił błąd przy przesyłaniu danych.";
            console.error(error);
        });

    } else {
        submitError.textContent = "Uzupełnij wszystkie dane";
    }
}

// CSRF helper
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
