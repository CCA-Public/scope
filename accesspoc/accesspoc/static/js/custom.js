$(document).ready(function() {
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
  $('body').on('change', '.custom-file-input', function(event) {
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
});
