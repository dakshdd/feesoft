
let student = null, monthData = {}, timer = null;
let studentRequestId = 0, searchRequestId = 0;

const months = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
];

const $ = id => document.getElementById(id);

const searchBox = $("searchBox"),
    studentList = $("studentList"),
    details = $("details"),
    monthBox = $("monthBox"),
    monthsDiv = $("months"),
    totalEl = $("selectedTotal"),
    balanceEl = $("studentBalance"),
    amountEl = $("amount"),
    paidAmountEl = $("paidAmount"),
    balanceAmountEl = $("balanceAmount"),
    lateFeeEl = $("lateFee"),
    saveBtn = $("saveBtn");


/* RESET */
function resetStudent() {
    student = null;
    monthData = {};

    details.innerHTML = "";
    monthsDiv.innerHTML = "";
    monthBox.style.display = "none";

    amountEl.value = "";
    paidAmountEl.value = "";
    balanceAmountEl.value = "";
    lateFeeEl.value = 0;
    totalEl.textContent = "0.00";
    balanceEl.textContent = "0.00";
}


/* SEARCH */
searchBox.addEventListener("input", function () {
    clearTimeout(timer);

    const q = this.value.trim();
    const requestId = ++searchRequestId;

    ++studentRequestId;
    resetStudent();
    studentList.innerHTML = "";

    if (!q) return;

    timer = setTimeout(async () => {
        try {
            const r = await fetch(
                FEE_URLS.autocomplete + "?q=" + encodeURIComponent(q),
                { cache: "no-store" }
            );

            const data = await r.json();

            if (requestId !== searchRequestId) return;

            studentList.innerHTML = "";

            if (!data.length) {
                const o = document.createElement("option");
                o.textContent = "No student found";
                o.disabled = true;
                studentList.appendChild(o);
                return;
            }

            data.forEach(s => {
                const o = document.createElement("option");
                o.value = s.adm_code;
                o.textContent =
                    `${s.student_name} | ${s.adm_code} | Class ${s.class || ""}`;

                studentList.appendChild(o);
            });

            studentList.selectedIndex = 0;
            await loadStudent();

        } catch (e) {
            console.error("Search error:", e);
        }
    }, 200);
});


studentList.addEventListener("change", loadStudent);


/* STUDENT LOAD */
async function loadStudent() {
    const adm = studentList.value;
    if (!adm) return;

    const requestId = ++studentRequestId;

    student = null;
    monthData = {};
    details.innerHTML = "";
    monthsDiv.innerHTML = "";
    monthBox.style.display = "none";

    try {
        const r = await fetch(
            FEE_URLS.details + "?adm_code=" + encodeURIComponent(adm),
            { cache: "no-store" }
        );

        const d = await r.json();

        // Ignore previous student response
        if (requestId !== studentRequestId) return;

        if (!d.adm_code) return;

        student = d;

        details.innerHTML = `
        <div class="info">
            <b>Name:</b> ${d.student_name}<br>
            <b>Admission:</b> ${d.adm_code}<br>
            <b>Class:</b> ${d.class || ""} ${d.section || ""}<br>
            <b>Father:</b> ${d.father_name || ""}<br>
            <b>Total Fee:</b> ₹${Number(d.total_fee || 0).toFixed(2)}<br>
            <b>Paid:</b> ₹${Number(d.paid_fee || 0).toFixed(2)}<br>
            <b>Balance:</b> ₹${Number(d.balance_fee || 0).toFixed(2)}
        </div>`;

        balanceEl.textContent =
            Number(d.balance_fee || 0).toFixed(2);

        amountEl.value = "";
        paidAmountEl.value = "";
        balanceAmountEl.value = "";
        lateFeeEl.value = 0;

        await loadMonths(adm, requestId);

    } catch (e) {
        if (e.name !== "AbortError")
            console.error("Student loading error:", e);
    }
}


/* BULK MONTH LOADING - ONLY ONE API REQUEST */
async function loadMonths(adm, requestId) {
    try {
        const r = await fetch(
            FEE_URLS.months + "?adm_code=" + encodeURIComponent(adm),
            { cache: "no-store" }
        );

        const data = await r.json();

        // Important: Never show old student's months
        if (requestId !== studentRequestId) return;
        if (!student || student.adm_code !== adm) return;

        if (!data.months) {
            throw new Error(data.error || "Months not found");
        }

        monthData = data.months;
        monthsDiv.innerHTML = "";

        months.forEach(month => {
            const d = monthData[month];
            if (!d) return;

            const paid = Number(d.balance || 0) <= 0;

            const div = document.createElement("div");

            div.className = "month" + (paid ? " paid" : "");

            div.innerHTML = `
                <label>
                    <input type="checkbox"
                        value="${month}"
                        ${paid ? "disabled" : ""}>
                    <b>${month}</b><br>

                    <span class="amount">
                        ₹${Number(d.balance || 0).toFixed(2)}
                    </span>

                    ${paid ? " - PAID" :
                    d.status === "Partial" ? " - PARTIAL" : ""}
                </label>
            `;

            const cb = div.querySelector("input");
            cb.addEventListener("change", calculateTotal);

            div.querySelector(".amount").addEventListener(
                "click", () => showMonthDetails(month)
            );

            monthsDiv.appendChild(div);
        });

        if (requestId !== studentRequestId) return;

        monthBox.style.display = "block";

    } catch (e) {
        console.error("Month loading error:", e);
    }
}


/* SELECTED MONTHS */
function selectedMonths() {
    return [...monthsDiv.querySelectorAll(
        "input[type=checkbox]:checked"
    )].map(x => x.value);
}


/* TOTAL */
function calculateTotal() {
    let total = 0;

    selectedMonths().forEach(month => {
        const d = monthData[month];
        if (d) total += Number(d.balance || 0);
    });

    total = Math.round(total * 100) / 100;

    amountEl.value = total.toFixed(2);
    paidAmountEl.value = total.toFixed(2);

    updateBalance();

    totalEl.textContent = total.toFixed(2);

    calculateLateFee();
}


/* BALANCE */
function updateBalance() {
    const total = Number(amountEl.value) || 0;
    const paid = Number(paidAmountEl.value) || 0;

    balanceAmountEl.value =
        Math.max(total - paid, 0).toFixed(2);
}

paidAmountEl.addEventListener("input", updateBalance);


/* LATE FEE - ₹5 PER DAY AFTER 10TH */
function calculateLateFee() {
    let fine = 0;
    const today = new Date();

    selectedMonths().forEach(month => {
        const i = months.indexOf(month);
        if (i < 0) return;

        let year = today.getFullYear();
        const monthNo = i + 4;

        if (monthNo <= 12 && today.getMonth() + 1 < 4)
            year--;

        const due = new Date(year, monthNo - 1, 10);

        if (today > due) {
            fine += Math.floor(
                (today - due) / 86400000
            ) * 5;
        }
    });

    lateFeeEl.value = Math.max(fine, 0);
}


/* MONTH DETAILS */
function showMonthDetails(month) {
    const d = monthData[month];
    if (!d) return;

    alert(`${month.toUpperCase()} FEE DETAILS

Annual Fee      : ₹${Number(d.annual_fee || 0).toFixed(2)}
Admission Fee   : ₹${Number(d.admission_fee || 0).toFixed(2)}
Tuition Fee     : ₹${Number(d.tuition_fee || 0).toFixed(2)}
Transport Fee   : ₹${Number(d.transport_fee || 0).toFixed(2)}
Development Fee : ₹${Number(d.devl_fee || 0).toFixed(2)}
E-Class Fee     : ₹${Number(d.eclass || 0).toFixed(2)}
Science Fee     : ₹${Number(d.science || 0).toFixed(2)}
Computer Fee    : ₹${Number(d.computer || 0).toFixed(2)}
K.Garten Fee    : ₹${Number(d.kgarten || 0).toFixed(2)}

----------------------------
FEE TOTAL       : ₹${Number(d.total || 0).toFixed(2)}
PAID            : ₹${Number(d.paid || 0).toFixed(2)}
BALANCE         : ₹${Number(d.balance || 0).toFixed(2)}
STATUS          : ${d.status || "Unpaid"}`);
}


/* SAVE PAYMENT */
saveBtn.addEventListener("click", async function () {

    if (!student)
        return alert("Please select student");

    const selectedStudent = student;
    const selected = selectedMonths();

    if (!selected.length)
        return alert("Please select at least one month");

    const total = Number(amountEl.value || 0);
    const paid = Number(paidAmountEl.value || 0);

    if (paid <= 0)
        return alert("Please enter Paid Amount");

    if (paid > total)
        return alert("Paid Amount cannot be greater than Amount Due.");

    if (paid > Number(selectedStudent.balance_fee || 0))
        return alert("Paid Amount cannot be greater than student balance.");

    const lateFee = Math.max(Number(lateFeeEl.value || 0), 0);

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
        const r = await fetch(FEE_URLS.pay, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                adm_code: selectedStudent.adm_code,
                months: selected,
                amount: paid,
                late_fee: lateFee,
                mode: $("mode").value,
                remark: $("remark").value
            })
        });

        const data = await r.json();

        if (!data.success) {
            alert(data.error || "Payment failed");
            return;
        }

        sessionStorage.setItem(
            "fee_saved_" + selectedStudent.adm_code,
            data.receipt_no
        );

        location.href = data.receipt_url;

    } catch (e) {
        console.error(e);
        alert("Server error. Please check payment before trying again.");

    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Payment";
    }
});
