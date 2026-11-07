/*
function  formatPrice(amount, includeSymbol) {
    if  (includeSymbol) {
            return `"$" + ${amount}`;
    } else (
            return amount;
    }
}

console.log(formatPrice('100', True));
*/

function doubleIt(x: Number, incSymb: boolean) {
    const x = a * 2;
    if (incSymb) {
        return ("$", x);
    } else {
        return x;
    }
}

const x = 5
console.log(doubleIt(x, true));
