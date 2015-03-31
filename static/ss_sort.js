(function($) {
  $('table.server-sortable').each(function() {
    var $table = $(this);
    var ordering = $table.attr('data-ordering'),
        order_by = $table.attr('data-order-by');

    $table.find('th.sort').each(function() {
      var $th = $(this);
      if ($th.attr('data-label') == order_by) {
        $th.addClass(ordering == "asc" ? "tablesorter-headerAsc" : "tablesorter-headerDesc");
        $th.on('click', function() {
          document.location.search = "?order_by=" + order_by + "&ordering=" + (ordering == "asc" ? "desc" : "asc");
        })
      } else {
        $th.on('click', function() {
          document.location.search = "?order_by=" + $th.attr('data-label');
        })
      }
    })
  })
})(jQuery);