import { validateEmail, validatePassword, handleSubmit} from "./user_utils.js";

let emailFlag = false;
let passwordFlag = false;

const email = document.getElementById("email");
const password = document.getElementById("password");
const submitButton = document.getElementById("submit-button");
const emailError = document.getElementById("email-error")
const passwordError = document.getElementById("password-error")
const submitButtonError = document.getElementById("submit-error")
const form = document.querySelector("form")

email.addEventListener("blur", function (e) {
    emailFlag = validateEmail(email, emailError);

}
)

password.addEventListener("blur", function () {
        passwordFlag = validatePassword(password, passwordError);
})


// submitButton.addEventListener("click", () => {
//     handleSubmit(form, submitButtonError, [emailFlag, passwordFlag]);
// });

submitButton.addEventListener("click", () => {
    handleSubmit(
        form,
        submitButtonError,
        [emailFlag, passwordFlag],
        "/sign-in/",
        (redirectUrl) => window.location.href = redirectUrl,
        (field, message) => {
            if (field === "email") emailError.textContent = message;
            if (field === "password") passwordError.textContent = message;
        }
    );
});