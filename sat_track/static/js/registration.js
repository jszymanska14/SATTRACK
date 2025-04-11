import { validateEmail, validatePassword, handleSubmit } from "./user_utils.js";


let emailFlag = false;
let passwordFlag = false;
let confirmPasswordFlag = false;
let enteredPassword = null;

const email = document.getElementById("email");
const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirm-password");
const submitButton = document.getElementById("submit-button");
const emailError = document.getElementById("email-error")
const passwordError = document.getElementById("password-error")
const confirmPasswordError = document.getElementById("confirm-password-error")
const submitButtonError = document.getElementById("submit-error")
const form = document.querySelector("form")


email.addEventListener("blur", function (e) {
    emailFlag = validateEmail(email, emailError);

}
)

password.addEventListener("blur", function () {
    passwordFlag = validatePassword(password, passwordError);
    if (passwordFlag) {
        enteredPassword = password.value;
    }
})

confirmPassword.addEventListener("blur", function () {

    const secondPassword = document.getElementById("confirm-password").value;

    if (secondPassword === enteredPassword) {
        confirmPasswordFlag = true;
        confirmPasswordError.textContent = ""
    } else {
        confirmPasswordFlag = false;
        confirmPasswordError.textContent = "hasło nie jest takie samo"
        document.getElementById("password").value = "";
    }
})

// submitButton.addEventListener("click", () => {
//     // handleSubmit(form, submitButtonError, [emailFlag, passwordFlag, confirmPasswordFlag]);
//     if (emailFlag && passwordFlag && confirmPasswordFlag) {
//         form.submit();
//     } else {
//         submitButtonError.textContent = "uzupełnij wszystkie dane";
//     }
// });

submitButton.addEventListener("click", () => {
    handleSubmit(
        form,
        submitButtonError,
        [emailFlag, passwordFlag, confirmPasswordFlag],
        "/register/",
        (redirectUrl) => window.location.href = redirectUrl,
        (field, message) => {
            if (field === "email") emailError.textContent = message;
            if (field === "password") passwordError.textContent = message;
            if (field === "confirm-password") confirmPasswordError.textContent = message;
        }
    );
});