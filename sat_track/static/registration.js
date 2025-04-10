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

email.addEventListener("blur", function (e) {
    const email = e.target.value;

    if(!email.includes('@')){
        emailFlag = false;
        emailError.textContent = "podaj poprawny email"
    }else if (email.length < 3)  {
        emailFlag = false;
        emailFlag.textContent = "podaj poprawny email";
    } else if(password.length > 65) {
        emailFlag = false;
        emailFlag.textContent = "podaj poprawny email";
    } else {
        emailFlag = true;
        emailError.textContent = ""
    }
}
)

password.addEventListener("blur", function () {

    const password = document.getElementById("password").value;

    if (password.length < 5)  {
        passwordFlag = false;
        passwordError.textContent = "hasło musi mieć przynajmniej 5 znaków";
        document.getElementById("password").value = "";
    } else if(password.length > 30) {
        passwordFlag = false;
        passwordError.textContent = "hasło musi mieć nie więcej niż 30 znaków";
        document.getElementById("password").value = "";
    } else if (!/[a-zA-Z]/.test(password)){
        passwordFlag = false;
        passwordError.textContent = "hasło musi mieć przynajmniej jedną literę"
        document.getElementById("password").value = "";
    } else if (!/\d/.test(password)){
        passwordFlag = false;
        passwordError.textContent = "hasło musi mieć przynajmniej jedną cyfrę"
        document.getElementById("password").value = "";
    } else {
        passwordFlag = true;
        enteredPassword = password;
        passwordError.textContent = ""
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

submitButton.addEventListener("click", function () {

    if(emailFlag && passwordFlag && confirmPasswordFlag){
        console.log("wszystko ok")
        document.querySelector('form').submit();  // Submit the form programmatically
    }else{
        console.log("nie jest ok")
    }
}
)