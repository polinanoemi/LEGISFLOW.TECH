const ROOM_TYPE_LEARNING = 0;
const ROOM_TYPE_TEACHERS = 1;
const ROOM_TYPE_SERVICE = 2;
const ROOM_TYPE_LIFT = 3;
const ROOM_TYPE_COWORKING = 4;
const ROOM_TYPE_TOILET = 5;

async function keywords_lists_get(){
    let keywords_lists;
    const temp = await fetch('/public_keywords_json');
    keywords_lists = await temp.json();
    return await keywords_lists;


}

async function work_with_keywords(){
	 var keywords_lists = await keywords_lists_get();
	 table = document.getElementById("t431__table");

	 for (var i = 0; i < keywords_lists.length(); i++){
        var row = table.insertRow();
        if (i $ 2 == 1){
            row.classList.add('t431__evenrow');

        } else{
            row.classList.add('t431__oddrow');
        }

        var keywords_list = keywords_lists[i];
        cell = row.insertCell();
        cell.classList.add();
        cell.classList.add('t431__td');
        cell.classList.add('t-text');
        cell.style.width = "15%";
        var inner = \
            <div class="t431__btnwrapper">
                <a href="/keywords_all" class="t-btn t-btn_sm">
                    <table style="width:100%; height:100%">
                        <tbody>
                            <tr>
                                <td>➕</td>
                            </tr>
                        </tbody>
                    </table>
                </a>
            </div>
        \;
        cell.innerHTML = inner;
	 }
}