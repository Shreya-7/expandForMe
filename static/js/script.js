document.addEventListener('DOMContentLoaded', function () {

    $('#signup-popover').popover({
        html: true,
        content: function() {
        return $('#signup-popover-content').html();
        }
    });
    $('#signin-popover').popover({
        html: true,
        content: function() {
        return $('#signin-popover-content').html();
        }
    });
    $('#add-upload-popover').popover({
        html: true,
        content: function() {
        return $('#add-upload-popover-content').html();
        }
    });
    $('#delete-upload-popover').popover({
        html: true,
        content: function() {
        return $('#delete-upload-popover-content').html();
        }
    });

    document.querySelector('#settings-modal').addEventListener('click', showSettings);

    document.querySelector('#phrase-modal').addEventListener('click', showPhrase);

    document.querySelector('#acro-delete-form').onsubmit = function() {
        refreshAlerts();
        return deleteAcronymsManual();
    }

    document.querySelector('#acro-add-form').onsubmit = function() {
        refreshAlerts();
        return addAcronymsManual();
    }

    document.querySelector('#acro-delete-file-form').onsubmit = function() {
        refreshAlerts();
        return deleteAcronymsFile();
    }

    document.querySelector('#acro-add-file-form').onsubmit = function() {
        refreshAlerts();
        return addAcronymsFile();
    }
});

function refreshAlerts() {
    document.querySelectorAll('.alert').forEach((alert)=>{

        alert.classList.remove('alert-success');
        alert.classList.remove('alert-warning');
        alert.classList.remove('alert-danger');
        alert.display = 'none';
    })
}

function showAlertMessage(alert_id, response) {

    refreshAlerts();

    const info_element = document.querySelector(`#${alert_id}`);

    response.json().then(response => {

        if (response.update_status == 1) {
            info_element.classList.add('alert-success')
        }

        else if (response.update_status == -1) {
            info_element.classList.add('alert-danger');
        }

        else {
            info_element.classList.add('alert-warning');
        }

        info_element.style.display = 'block';
        document.querySelector(`#${alert_id} span strong`).innerHTML = response.message;
    })
}

function addAcronyms(data) {

    fetch('/add_acronyms', {
        method: 'POST',
        body: data
    })
    .then((response) => {
        showAlertMessage('acro-phrase-alert', response);
    })

    return false;
}

function addAcronymsManual() {

    var formData = new FormData(document.querySelector('#acro-add-form'));
    const data = new URLSearchParams();

    for (const pair of formData) {
        data.append(pair[0], pair[1]);
    }

    data.append("mode", "manual");
    return addAcronyms(data);
}

function addAcronymsFile() {
    
    var data = new FormData();
    data.append("add_acronym_file", document.getElementById('add-acronym-file').files[0]);
    data.append("mode", "file");

    return addAcronyms(data);
}

function deleteAcronyms(data) {

    fetch('/delete_acronyms', {
        method: 'POST',
        body: data
    })
    .then((response) => {
        showAlertMessage('acro-phrase-alert', response);
    })

    return false;
}

function deleteAcronymsFile() {
    
    var data = new FormData();
    data.append("delete_acronym_file", document.getElementById('delete-acronym-file').files[0]);
    data.append("mode", "file");

    return deleteAcronyms(data);
}

function deleteAcronymsManual() {

    
    var formData = new FormData(document.querySelector('#acro-delete-form'));
    const data = new URLSearchParams();

    for (const pair of formData) {
        data.append(pair[0], pair[1]);
    }

    data.append("mode", "manual");
    return deleteAcronyms(data);
}

function showPhrase() {
    var checkExist = setInterval(function () {
        if ($('.modal').length) {
            clearInterval(checkExist);
        }
    }, 100);

    removeAlert('phrase-modal');

    fetch('/get_phrase')
    .then(response => response.json())
    .then(response => {
        document.querySelector('input[name=phrase]').value = response['phrase'];
    })
    .catch(error => {
        console.log('Error: ' + error);
    });

    document.querySelector('#phrase-edit-form').onsubmit =  function(event){
        return savePhrase();
    };
}

function savePhrase() {

    var formData = new FormData(document.querySelector('#phrase-edit-form'));
    const data = new URLSearchParams();

    for (const pair of formData) {
        data.append(pair[0], pair[1]);
    }

    fetch('/save_phrase', {
        method: 'POST',
        body: data
    })
    .then((response) => {
        
        showAlertMessage('phrase-alert', response);

    })

    return false;
}

function showSettings() {

    var checkExist = setInterval(function () {
        if ($('.modal').length) {
            clearInterval(checkExist);
        }
    }, 100);

    removeAlert('settings-modal');

    fetch('/get_settings')
        .then(response => response.json())
        .then(response => {
            for (var id in response) {
                if (response[id] != false)
                    document.querySelector('#' + id).checked = true;
            }
        })
        .catch(error => {
            console.log('Error: ', error);
        })

    document.querySelector('#settings-form').onsubmit =  function(event){
        return saveSettings();
    };
}

function saveSettings() {
    var formData = new FormData(document.querySelector('#settings-form'));
    const data = new URLSearchParams();

    var item_count =0;
    for (const pair of formData) {
        if (pair[0] === 'comment_item')
            item_count+=1;
    }

    for (const pair of formData) {
        if (item_count==2 && pair[0] === 'comment_item')
            data.append('comment_item', 2)
        else
            data.append(pair[0], pair[1]);
    }

    console.log(data.toString());

    fetch('/save_settings', {
        method: 'POST',
        body: data
    })
    .then((response)=>{

        showAlertMessage('settings-alert', response);

    })

    return false;
}