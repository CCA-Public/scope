// Filter by Department
$(".filter").click(function(e) {
    var selectDepartment = $(this).text().trim();
    filter(selectDepartment)
            e.preventDefault();
});

// Filter function
function filter(e) {
    var regex = new RegExp('\\b' + e + '\\b');
    $('.collection').hide().filter(function () {
        return regex.test($(this).data('department'))
    }).show();
}

// Show all button
$(".all").click(function(e) {
    $('.collection').show()
});
