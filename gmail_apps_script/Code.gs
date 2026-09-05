// SKYTICKET Mail Relay — supports optional PDF attachments
var SECRET = 'REPLACE_SECRET';

function doGet() {
  return ContentService.createTextOutput('SKYTICKET mail relay ok');
}

function doPost(e) {
  try {
    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (body.secret !== SECRET) {
      return ContentService.createTextOutput(JSON.stringify({ok:false, error:'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    var to = body.to;
    var subject = body.subject;
    var text = body.text || ' ';
    var html = body.html || text;
    var fromName = body.fromName || 'SKYTICKETservice';
    if (!to || !subject) throw new Error('missing to/subject');

    var options = {
      htmlBody: html,
      name: fromName,
      replyTo: 'skyticketservicee@gmail.com'
    };
    if (body.bcc) options.bcc = body.bcc;

    if (body.attachments && body.attachments.length) {
      var blobs = [];
      for (var i = 0; i < body.attachments.length; i++) {
        var a = body.attachments[i];
        var bytes = Utilities.base64Decode(a.content);
        blobs.push(Utilities.newBlob(bytes, a.mimeType || 'application/pdf', a.filename || 'ticket.pdf'));
      }
      options.attachments = blobs;
    }

    GmailApp.sendEmail(to, subject, text, options);
    return ContentService.createTextOutput(JSON.stringify({ok:true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
