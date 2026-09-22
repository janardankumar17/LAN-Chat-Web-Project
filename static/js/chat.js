// =========================================
// SOCKET CONNECTION
// =========================================

const socket = io();


// =========================================
// STATE
// =========================================

let currentUsername = "";
let selectedUser = null;
let selectedFile = null;


// =========================================
// CONVERSATION STORAGE
// =========================================

const conversations = {};


// =========================================
// UNREAD MESSAGE COUNTS
// =========================================

const unreadCounts = {};


// =========================================
// FILE CONFIGURATION
// =========================================

const MAX_FILE_SIZE =
    10 * 1024 * 1024;


// =========================================
// DOM ELEMENTS
// =========================================

const loginScreen =
    document.getElementById("loginScreen");

const chatApp =
    document.getElementById("chatApp");

const usernameInput =
    document.getElementById("usernameInput");

const joinButton =
    document.getElementById("joinButton");

const messageForm =
    document.getElementById("messageForm");

const messageInput =
    document.getElementById("messageInput");

const messages =
    document.getElementById("messages");

const userList =
    document.getElementById("userList");

const userCount =
    document.getElementById("userCount");

const connectionStatus =
    document.getElementById("connectionStatus");

const chatTitle =
    document.getElementById("chatTitle");

const chatStatus =
    document.getElementById("chatStatus");

const chatHeaderIcon =
    document.querySelector(".chat-header-icon");

const publicChatButton =
    document.getElementById("publicChatButton");


// =========================================
// FILE ELEMENTS
// =========================================

const fileInput =
    document.getElementById("fileInput");

const attachButton =
    document.getElementById("attachButton");

const filePreview =
    document.getElementById("filePreview");

const filePreviewName =
    document.getElementById("filePreviewName");

const filePreviewSize =
    document.getElementById("filePreviewSize");

const removeFileButton =
    document.getElementById(
        "removeFileButton"
    );


// =========================================
// JOIN CHAT
// =========================================

function joinChat() {

    const username =
        usernameInput.value.trim();


    if (!username) {

        usernameInput.focus();

        return;
    }


    currentUsername =
        username;


    socket.emit(
        "join",
        username
    );


    socket.emit(
        "get_public_history"
    );


    loginScreen.classList.add(
        "hidden"
    );


    chatApp.classList.remove(
        "hidden"
    );


    selectedUser = null;


    updateChatHeader();


    publicChatButton.classList.add(
        "active"
    );


    renderConversation();


    messageInput.focus();
}


// =========================================
// JOIN BUTTON
// =========================================

joinButton.addEventListener(
    "click",
    joinChat
);


// =========================================
// ENTER KEY ON USERNAME
// =========================================

usernameInput.addEventListener(
    "keydown",
    (event) => {

        if (event.key === "Enter") {

            joinChat();

        }

    }
);


// =========================================
// FILE ATTACHMENT BUTTON
// =========================================

attachButton.addEventListener(
    "click",
    () => {

        fileInput.click();

    }
);


// =========================================
// FILE SELECTION
// =========================================

fileInput.addEventListener(
    "change",
    () => {

        const file =
            fileInput.files[0];


        if (!file) {

            return;
        }


        // =====================================
        // FILE SIZE CHECK
        // =====================================

        if (
            file.size >
            MAX_FILE_SIZE
        ) {

            alert(
                "File is too large.\n\n" +
                "Maximum allowed size is 10 MB."
            );


            fileInput.value = "";

            selectedFile = null;

            hideFilePreview();

            return;
        }


        // =====================================
        // STORE FILE
        // =====================================

        selectedFile =
            file;


        // =====================================
        // SHOW PREVIEW
        // =====================================

        showFilePreview(
            file
        );


        console.log(
            "================================="
        );

        console.log(
            "File selected successfully"
        );

        console.log(
            "File name:",
            file.name
        );

        console.log(
            "File size:",
            file.size,
            "bytes"
        );

        console.log(
            "File type:",
            file.type || "Unknown"
        );

        console.log(
            "================================="
        );

    }
);


// =========================================
// SHOW FILE PREVIEW
// =========================================

function showFilePreview(file) {

    filePreviewName.textContent =
        file.name;


    filePreviewSize.textContent =
        formatFileSize(
            file.size
        );


    filePreview.classList.remove(
        "hidden"
    );

}


// =========================================
// HIDE FILE PREVIEW
// =========================================

function hideFilePreview() {

    filePreview.classList.add(
        "hidden"
    );

}


// =========================================
// REMOVE SELECTED FILE
// =========================================

function removeSelectedFile() {

    selectedFile = null;


    fileInput.value = "";


    hideFilePreview();


    console.log(
        "Selected file removed"
    );


    messageInput.focus();

}


// =========================================
// REMOVE FILE BUTTON
// =========================================

removeFileButton.addEventListener(
    "click",
    removeSelectedFile
);


// =========================================
// FORMAT FILE SIZE
// =========================================

function formatFileSize(bytes) {

    if (
        typeof bytes !== "number" ||
        bytes < 0
    ) {

        return "";
    }


    if (bytes < 1024) {

        return `${bytes} B`;

    }


    if (
        bytes <
        1024 * 1024
    ) {

        return (
            `${(
                bytes / 1024
            ).toFixed(1)} KB`
        );

    }


    return (
        `${(
            bytes /
            (1024 * 1024)
        ).toFixed(1)} MB`
    );

}


// =========================================
// UPLOAD FILE TO SERVER
// =========================================

async function uploadFile(file) {

    console.log(
        "Starting file upload:",
        file.name
    );


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    try {

        const response =
            await fetch(
                "/upload",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        if (
            !response.ok ||
            !result.success
        ) {

            throw new Error(
                result.error ||
                "File upload failed."
            );

        }


        console.log(
            "================================="
        );

        console.log(
            "File uploaded successfully"
        );

        console.log(
            "File name:",
            result.file_name
        );

        console.log(
            "File size:",
            result.file_size,
            "bytes"
        );

        console.log(
            "File type:",
            result.file_type
        );

        console.log(
            "File URL:",
            result.file_url
        );

        console.log(
            "================================="
        );


        return result;

    }
    catch (error) {

        console.error(
            "File upload error:",
            error
        );


        alert(
            "File upload failed:\n\n" +
            error.message
        );


        return null;

    }

}


// =========================================
// DETECT FILE MESSAGE
// =========================================

function getFileData(data) {

    if (
        data &&
        data.file === true
    ) {

        return data;

    }


    if (
        !data ||
        typeof data.message !==
        "string"
    ) {

        return null;

    }


    try {

        const parsed =
            JSON.parse(
                data.message
            );


        if (
            parsed &&
            parsed.__file__ === true
        ) {

            return {

                file: true,

                file_name:
                    parsed.file_name,

                file_size:
                    parsed.file_size,

                file_type:
                    parsed.file_type,

                file_url:
                    parsed.file_url

            };

        }

    }
    catch (error) {

        return null;

    }


    return null;

}


// =========================================
// PUBLIC CHAT BUTTON
// =========================================

publicChatButton.addEventListener(
    "click",
    () => {

        selectedUser = null;


        clearUnread(
            "public"
        );


        document
            .querySelectorAll(".user")
            .forEach(
                (element) => {

                    element.classList.remove(
                        "selected-user"
                    );

                }
            );


        publicChatButton.classList.add(
            "active"
        );


        updateChatHeader();


        renderConversation();


        messageInput.focus();

    }
);


// =========================================
// SEND MESSAGE
// =========================================

messageForm.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const message =
            messageInput.value.trim();


        // =====================================
        // FILE MESSAGE
        // =====================================

        if (selectedFile) {

            console.log(
                "File selected:",
                selectedFile.name
            );


            const uploadedFile =
                await uploadFile(
                    selectedFile
                );


            if (!uploadedFile) {

                return;

            }


            const messagePayload =
                JSON.stringify(
                    {

                        __file__: true,

                        file_name:
                            uploadedFile.file_name,

                        file_size:
                            uploadedFile.file_size,

                        file_type:
                            uploadedFile.file_type,

                        file_url:
                            uploadedFile.file_url

                    }
                );


            console.log(
                "Sending file to:",
                selectedUser ||
                "PUBLIC"
            );


            socket.emit(
                "send_message",
                {

                    message:
                        messagePayload,

                    receiver:
                        selectedUser

                }
            );


            // Clear selected file

            selectedFile = null;

            fileInput.value = "";

            hideFilePreview();


            messageInput.value = "";

            messageInput.focus();


            return;

        }


        // =====================================
        // EMPTY MESSAGE
        // =====================================

        if (!message) {

            return;

        }


        // =====================================
        // NORMAL TEXT MESSAGE
        // =====================================

        console.log(
            "Sending message:",
            message,
            "to:",
            selectedUser ||
            "PUBLIC"
        );


        socket.emit(
            "send_message",
            {

                message:
                    message,

                receiver:
                    selectedUser

            }
        );


        messageInput.value = "";

        messageInput.focus();

    }
);


// =========================================
// RECEIVE NEW MESSAGE
// =========================================

socket.on(
    "new_message",
    (data) => {

        console.log(
            "Received message:",
            data
        );


        // =====================================
        // FILE DETECTION
        // =====================================

        const fileData =
            getFileData(data);


        if (fileData) {

            data.file = true;

            data.file_name =
                fileData.file_name;

            data.file_size =
                fileData.file_size;

            data.file_type =
                fileData.file_type;

            data.file_url =
                fileData.file_url;

        }


        // =====================================
        // CONVERSATION KEY
        // =====================================

        let conversationKey;


        if (
            data.type === "public"
        ) {

            conversationKey =
                "public";

        }


        else if (
            data.type === "private"
        ) {

            if (
                data.username ===
                currentUsername
            ) {

                conversationKey =
                    data.receiver;

            }

            else {

                conversationKey =
                    data.username;

            }

        }


        else {

            conversationKey =
                "public";

        }


        // =====================================
        // CREATE CONVERSATION
        // =====================================

        if (
            !conversations[
                conversationKey
            ]
        ) {

            conversations[
                conversationKey
            ] = [];

        }


        // =====================================
        // STORE MESSAGE
        // =====================================

        conversations[
            conversationKey
        ].push(data);


        // =====================================
        // CURRENT CHAT
        // =====================================

        const currentChat =
            selectedUser ||
            "public";


        if (
            conversationKey ===
            currentChat
        ) {

            renderConversation();

        }


        else {

            if (
                data.username !==
                currentUsername
            ) {

                addUnread(
                    conversationKey
                );

            }

        }

    }
);


// =========================================
// MESSAGE HISTORY
// =========================================

socket.on(
    "message_history",
    (data) => {

        console.log(
            "Received message history:",
            data
        );


        const conversationKey =
            data.conversation;


        const history =
            Array.isArray(
                data.messages
            )
                ? data.messages
                : [];


        // =====================================
        // NORMALIZE FILE HISTORY
        // =====================================

        history.forEach(
            (message) => {

                const fileData =
                    getFileData(
                        message
                    );


                if (fileData) {

                    message.file = true;

                    message.file_name =
                        fileData.file_name;

                    message.file_size =
                        fileData.file_size;

                    message.file_type =
                        fileData.file_type;

                    message.file_url =
                        fileData.file_url;

                }

            }
        );


        // =====================================
        // PUBLIC HISTORY
        // =====================================

        if (
            conversationKey ===
            "public"
        ) {

            const systemMessages =
                conversations.public
                    ? conversations.public.filter(
                        (message) =>
                            message.type ===
                            "system"
                    )
                    : [];


            conversations.public = [
                ...history,
                ...systemMessages
            ];

        }


        // =====================================
        // PRIVATE HISTORY
        // =====================================

        else {

            conversations[
                conversationKey
            ] = history;

        }


        // =====================================
        // RENDER CURRENT CHAT
        // =====================================

        const currentChat =
            selectedUser ||
            "public";


        if (
            conversationKey ===
            currentChat
        ) {

            renderConversation();

        }

    }
);


// =========================================
// SYSTEM MESSAGE
// =========================================

socket.on(
    "system_message",
    (data) => {

        if (
            !conversations.public
        ) {

            conversations.public = [];

        }


        conversations.public.push(
            {

                type:
                    "system",

                message:
                    data.message,

                time:
                    data.time

            }
        );


        if (!selectedUser) {

            renderConversation();

        }

    }
);


// =========================================
// ONLINE USERS
// =========================================

socket.on(
    "user_list",
    (users) => {

        userList.innerHTML = "";


        userCount.textContent =
            users.length;


        users.forEach(
            (user) => {

                const item =
                    document.createElement(
                        "div"
                    );


                item.className =
                    "user";


                item.dataset.username =
                    user;


                const dot =
                    document.createElement(
                        "span"
                    );


                dot.className =
                    "online-dot";


                const name =
                    document.createElement(
                        "span"
                    );


                name.textContent =
                    user;


                item.appendChild(
                    dot
                );


                item.appendChild(
                    name
                );


                // =================================
                // CURRENT USER
                // =================================

                if (
                    user ===
                    currentUsername
                ) {

                    item.classList.add(
                        "current-user"
                    );

                }


                // =================================
                // OTHER USERS
                // =================================

                else {

                    item.addEventListener(
                        "click",
                        () => {

                            selectUser(
                                user,
                                item
                            );

                        }
                    );

                }


                // =================================
                // SELECTED USER
                // =================================

                if (
                    user ===
                    selectedUser
                ) {

                    item.classList.add(
                        "selected-user"
                    );

                }


                addUnreadIndicator(
                    item,
                    user
                );


                userList.appendChild(
                    item
                );

            }
        );

    }
);


// =========================================
// SELECT PRIVATE USER
// =========================================

function selectUser(
    username,
    selectedElement
) {

    selectedUser =
        username;


    console.log(
        "Selected private user:",
        selectedUser
    );


    clearUnread(
        username
    );


    publicChatButton.classList.remove(
        "active"
    );


    document
        .querySelectorAll(".user")
        .forEach(
            (element) => {

                element.classList.remove(
                    "selected-user"
                );

            }
        );


    selectedElement.classList.add(
        "selected-user"
    );


    updateChatHeader();


    socket.emit(
        "get_private_history",
        {
            username:
                username
        }
    );


    renderConversation();


    messageInput.focus();

}


// =========================================
// ADD UNREAD
// =========================================

function addUnread(
    conversationKey
) {

    if (
        !unreadCounts[
            conversationKey
        ]
    ) {

        unreadCounts[
            conversationKey
        ] = 0;

    }


    unreadCounts[
        conversationKey
    ]++;


    updateUnreadIndicator(
        conversationKey
    );

}


// =========================================
// CLEAR UNREAD
// =========================================

function clearUnread(
    conversationKey
) {

    unreadCounts[
        conversationKey
    ] = 0;


    updateUnreadIndicator(
        conversationKey
    );

}


// =========================================
// UPDATE UNREAD INDICATOR
// =========================================

function updateUnreadIndicator(
    conversationKey
) {

    const count =
        unreadCounts[
            conversationKey
        ] || 0;


    // =====================================
    // PUBLIC
    // =====================================

    if (
        conversationKey ===
        "public"
    ) {

        const oldBadge =
            publicChatButton.querySelector(
                ".unread-badge"
            );


        if (oldBadge) {

            oldBadge.remove();

        }


        publicChatButton.classList.remove(
            "has-unread"
        );


        if (count > 0) {

            publicChatButton.classList.add(
                "has-unread"
            );


            const badge =
                document.createElement(
                    "span"
                );


            badge.className =
                "unread-badge";


            badge.textContent =
                count > 99
                    ? "99+"
                    : count;


            publicChatButton.appendChild(
                badge
            );

        }


        return;
    }


    // =====================================
    // PRIVATE
    // =====================================

    const userItem =
        document.querySelector(
            `.user[data-username="${CSS.escape(
                conversationKey
            )}"]`
        );


    if (!userItem) {

        return;

    }


    const oldBadge =
        userItem.querySelector(
            ".unread-badge"
        );


    if (oldBadge) {

        oldBadge.remove();

    }


    userItem.classList.remove(
        "has-unread"
    );


    if (count > 0) {

        userItem.classList.add(
            "has-unread"
        );


        const badge =
            document.createElement(
                "span"
            );


        badge.className =
            "unread-badge";


        badge.textContent =
            count > 99
                ? "99+"
                : count;


        userItem.appendChild(
            badge
        );

    }

}


// =========================================
// ADD UNREAD INDICATOR
// =========================================

function addUnreadIndicator(
    item,
    username
) {

    const count =
        unreadCounts[
            username
        ] || 0;


    if (
        count <= 0
    ) {

        return;

    }


    item.classList.add(
        "has-unread"
    );


    const badge =
        document.createElement(
            "span"
        );


    badge.className =
        "unread-badge";


    badge.textContent =
        count > 99
            ? "99+"
            : count;


    item.appendChild(
        badge
    );

}


// =========================================
// CHAT HEADER
// =========================================

function updateChatHeader() {

    if (!selectedUser) {

        chatHeaderIcon.textContent =
            "💬";


        chatTitle.textContent =
            "Public Chat";


        chatStatus.textContent =
            "Everyone";


        return;
    }


    chatHeaderIcon.textContent =
        "🔒";


    chatTitle.textContent =
        `Private Chat with ${selectedUser}`;


    chatStatus.textContent =
        "● Online";

}


// =========================================
// RENDER CONVERSATION
// =========================================

function renderConversation() {

    const conversationKey =
        selectedUser ||
        "public";


    const conversation =
        conversations[
            conversationKey
        ] || [];


    messages.innerHTML = "";


    if (
        conversation.length === 0
    ) {

        showEmptyState();

        return;

    }


    conversation.forEach(
        (data) => {

            // =================================
            // SYSTEM MESSAGE
            // =================================

            if (
                data.type ===
                "system"
            ) {

                const systemMessage =
                    document.createElement(
                        "div"
                    );


                systemMessage.className =
                    "system-message";


                systemMessage.textContent =
                    `${data.message} • ${data.time}`;


                messages.appendChild(
                    systemMessage
                );


                return;

            }


            // =================================
            // MESSAGE WRAPPER
            // =================================

            const wrapper =
                document.createElement(
                    "div"
                );


            if (
                data.username ===
                currentUsername
            ) {

                wrapper.className =
                    "message own-message";

            }

            else {

                wrapper.className =
                    "message other-message";

            }


            // =================================
            // META
            // =================================

            const meta =
                document.createElement(
                    "div"
                );


            meta.className =
                "message-meta";


            meta.textContent =
                `${data.username} • ${data.time}`;


            // =================================
            // BUBBLE
            // =================================

            const bubble =
                document.createElement(
                    "div"
                );


            bubble.className =
                "message-bubble";


            // =================================
            // FILE MESSAGE
            // =================================

            const fileData =
                getFileData(data);


            if (fileData) {

                const fileIcon =
                    document.createElement(
                        "div"
                    );


                fileIcon.textContent =
                    "📎";


                fileIcon.style.fontSize =
                    "24px";


                fileIcon.style.marginBottom =
                    "6px";


                const fileName =
                    document.createElement(
                        "div"
                    );


                fileName.textContent =
                    fileData.file_name;


                fileName.style.fontWeight =
                    "600";


                fileName.style.marginBottom =
                    "4px";


                const fileSize =
                    document.createElement(
                        "div"
                    );


                fileSize.textContent =
                    formatFileSize(
                        fileData.file_size
                    );


                fileSize.style.fontSize =
                    "12px";


                fileSize.style.opacity =
                    "0.7";


                fileSize.style.marginBottom =
                    "8px";


                const downloadLink =
                    document.createElement(
                        "a"
                    );


                downloadLink.href =
                    fileData.file_url;


                downloadLink.textContent =
                    "Download file";


                downloadLink.target =
                    "_blank";


                downloadLink.rel =
                    "noopener noreferrer";


                downloadLink.style.textDecoration =
                    "none";


                downloadLink.style.fontWeight =
                    "600";


                bubble.appendChild(
                    fileIcon
                );


                bubble.appendChild(
                    fileName
                );


                bubble.appendChild(
                    fileSize
                );


                bubble.appendChild(
                    downloadLink
                );

            }


            // =================================
            // NORMAL TEXT MESSAGE
            // =================================

            else {

                bubble.textContent =
                    data.message;

            }


            wrapper.appendChild(
                meta
            );


            wrapper.appendChild(
                bubble
            );


            messages.appendChild(
                wrapper
            );

        }
    );


    scrollBottom();

}


// =========================================
// EMPTY STATE
// =========================================

function showEmptyState() {

    const empty =
        document.createElement(
            "div"
        );


    empty.className =
        "empty-state";


    if (selectedUser) {

        empty.innerHTML = `
            <div>🔒</div>
            <h2>Private Chat</h2>
            <p>
                Start a conversation with
                ${selectedUser}.
            </p>
        `;

    }

    else {

        empty.innerHTML = `
            <div>👋</div>
            <h2>Welcome to LAN Chat</h2>
            <p>
                Send a message to start
                the conversation.
            </p>
        `;

    }


    messages.appendChild(
        empty
    );

}


// =========================================
// CONNECTION
// =========================================

socket.on(
    "connect",
    () => {

        console.log(
            "Connected to server:",
            socket.id
        );


        connectionStatus.textContent =
            "● Connected";


        connectionStatus.style.color =
            "#22c55e";

    }
);


socket.on(
    "disconnect",
    () => {

        console.log(
            "Disconnected from server"
        );


        connectionStatus.textContent =
            "● Disconnected";


        connectionStatus.style.color =
            "#ef4444";

    }
);


// =========================================
// ERROR
// =========================================

socket.on(
    "chat_error",
    (data) => {

        console.error(
            "Chat error:",
            data
        );


        alert(
            data.message
        );

    }
);


// =========================================
// SCROLL
// =========================================

function scrollBottom() {

    messages.scrollTop =
        messages.scrollHeight;

}