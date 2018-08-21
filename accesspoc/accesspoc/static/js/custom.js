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
});
