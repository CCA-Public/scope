$(document).ready(function() {
  /* Trigger datepickers. */
  $('input.with-datepicker').datepicker({
    format: 'yyyy-mm-dd',
    autoclose: true,
    clearBtn: true,
    orientation: 'bottom auto',
    language: $('html')[0].lang,
  });
  
  /*
  Language link click listener:
  Changes the language hidden input value on the sibling language
  form with the language clode included in the 'data-language'
  attribute from the link and submits the form.
  */
  $('body').on('click', 'a.change-language', function(event) {
    event.preventDefault();
    var $this = $(this);
    var $form = $($this.siblings('#language-form')[0]);
    $form.find('input[name="language"]').val($this.data('language'));
    $form.submit();
  });

  /*
  Custom file imput listener:
  Changes the placeholder of the Bootstrap custom file input.
  Sets it to the filename when it's populated, otherwise uses
  the `data-placeholder` attribute value.
  */
  $('body').on('change', '.custom-file-input', function() {
    var $this = $(this);
    var value = $this.val();
    var $label = $($this.siblings('.custom-file-label')[0]);
    if (value) {
      // Show filename only
      $label.html(value.replace(/^.*[\\\/]/, ''));
    } else {
      $label.html($this.data('placeholder'));
    }
  });

  /* Avoid closing the aggregations drop-down on inside click. */
  $('body').on('click', '.aggs-dropdown', function (event) {
    event.stopPropagation();
  });

  /*
  Filter aggregation items based on `agg-query` input:
  If a backend endpoint is implement to allow pagination in the
  aggregation drop-downs, this query should also be passed to
  perform the filtering in there.
  */
  $('body').on('keyup', '.aggs-query-input', function () {
    var $this = $(this);
    var query = $this.val().trim();
    var $items = $($this.closest('.aggs-dropdown').find('.dropdown-item'));

    // Show all items on empty query
    if (!query.length) {
      $items.removeClass('d-none');
      return;
    }

    // Show/hide based on query value, case insensitive
    query = query.toLowerCase();
    $items.each(function() {
      var $item = $(this);
      var $checkbox = $($item.find('input[type="checkbox"]')[0]);
      var value = $checkbox.val().trim().toLowerCase();
      if (value.indexOf(query) >= 0) {
        $item.removeClass('d-none');
      } else {
        // Uncheck when hiding
        $checkbox.prop('checked', false);
        $item.addClass('d-none');
      }
    });
  });

  /*
  Submit digital files filters form when enter is pressed in the query input.
  By default it goes to first drop-down button from the input group.
  */
  $('body').on('keypress', '.digital-file-filters input[name="query"]', function (event) {
    if (event.which == 13) {
      $(this).closest('form').submit();
    }
  });
});
