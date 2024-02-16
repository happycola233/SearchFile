import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fnmatch
import shutil
import subprocess
import threading
import queue
import send2trash

# 多线程搜索文件
def search_files_thread(directory, keyword):
    global search_in_progress
    search_in_progress = True
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not search_in_progress:  # 允许停止搜索
                return
            if not any(char in keyword for char in '*?'):
                if keyword.lower() in file.lower():
                    found_files_queue.put((file, os.path.join(root, file)))
            elif fnmatch.fnmatch(file, keyword):
                found_files_queue.put((file, os.path.join(root, file)))
    search_in_progress = False

# 更新搜索结果的函数
def update_search_results():
    if not search_in_progress and found_files_queue.empty():
        # messagebox.showinfo("搜索完成", "搜索已完成。")
        status_var.set("搜索已完成。")
        return
    while not found_files_queue.empty():
        file_name, file_path = found_files_queue.get()
        display_text = file_path if show_full_path.get() else file_name  # 根据复选框状态选择显示方式
        result_listbox.insert("", tk.END, text=display_text, values=[file_path])
    root.after(100, update_search_results) # 每100毫秒调用一次自身以更新结果

# 开始搜索的函数
def start_search():
    status_var.set("")
    keyword = keyword_entry.get()
    directory = directory_entry.get()
    if not directory:
        messagebox.showinfo("错误", "请选择一个目录。")
        return
    result_listbox.delete(*result_listbox.get_children())  # 清除先前的结果
    threading.Thread(target=search_files_thread, args=(directory, keyword)).start()
    update_search_results()  # 开始更新搜索结果

# 停止搜索的函数
def stop_search():
    global search_in_progress
    search_in_progress = False

# 处理“浏览”按钮单击事件的函数
def browse_directory():
    directory = filedialog.askdirectory()
    directory_entry.delete(0, tk.END)
    directory_entry.insert(0, directory.replace("/", "\\"))

# 切换文件显示方式的函数
def toggle_display_mode():
    # 清除当前的搜索结果并重新显示，以反映新的显示模式
    current_items = result_listbox.get_children()
    files_info = [(result_listbox.item(item)["text"], result_listbox.item(item)["values"][0]) for item in current_items]
    result_listbox.delete(*current_items)
    for file_name, file_path in files_info:
        display_text = file_path if show_full_path.get() else os.path.basename(file_path)
        result_listbox.insert("", tk.END, text=display_text, values=[file_path])

# 处理复制文件路径到剪贴板的函数
def copy_file_path():
    selection = result_listbox.selection()
    if selection:
        file_paths = [result_listbox.item(item)['values'][0].replace("/", "\\") for item in selection]
        file_paths_str = "\n".join(file_paths)
        try:
            root.clipboard_clear()
            root.clipboard_append(file_paths_str)
            root.update()
            # messagebox.showinfo("成功", "选中的文件路径已复制到剪贴板！")
            status_var.set("选中的文件路径已复制到剪贴板！")
        except Exception as e:
            messagebox.showerror("错误", f"无法复制文件路径：{e}")
    else:
        messagebox.showinfo("提示", "请选择要复制的文件路径。")

# 处理打开文件位置的函数
def open_location():
    selection = result_listbox.selection()
    if selection:
        file_path = result_listbox.item(selection[0])['values'][0]
        file_path = file_path.replace("/", "\\")  # 统一使用 \
        try:
            subprocess.Popen(['explorer', '/select,', file_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件位置：{e}")
    else:
        messagebox.showinfo("提示", "请选择要打开位置的文件。")

# 处理复制文件到新位置的函数
def copy_to_new_location():
    selection = result_listbox.selection()
    if selection:
        new_location = filedialog.askdirectory().replace('/', '\\')
        if new_location:
            for item in selection:
                file_path = result_listbox.item(item)['values'][0].replace("/", "\\")
                try:
                    destination = os.path.join(new_location, os.path.basename(file_path)).replace("/", "\\")
                    shutil.copy2(file_path, destination)
                    status_var.set(f"选中的文件已复制到 {new_location}")
                except Exception as e:
                    messagebox.showerror("错误", f"无法复制文件：{e}")
    else:
        messagebox.showinfo("提示", "请选择要复制的文件。")

# 处理打开文件的函数
def open_file():
    selection = result_listbox.selection()
    if selection:
        for item in selection:
            file_path = result_listbox.item(item)['values'][0]
            file_path = file_path.replace("/", "\\")  # 统一使用 \
            try:
                subprocess.Popen(['start', '', file_path], shell=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件 {file_path}：{e}")
    else:
        messagebox.showinfo("提示", "请选择要打开的文件。")

# 删除文件的函数
def delete_files():
    selection = result_listbox.selection()
    if selection:
        if messagebox.askyesno("确认删除", "确定要删除选中的文件吗？这些文件将被移动到回收站。"):
            for item in selection:
                file_path = result_listbox.item(item)['values'][0]
                try:
                    send2trash.send2trash(file_path)  # 将文件移动到回收站
                    result_listbox.delete(item)  # 从列表中移除已删除的项
                except Exception as e:
                    messagebox.showerror("错误", f"删除文件时出错：{e}")
            # messagebox.showinfo("删除成功", "选中的文件已成功移动到回收站。")
            status_var.set("选中的文件已成功移动到回收站。")
    else:
        messagebox.showinfo("提示", "请选择要删除的文件。")

def popup_menu(event):
    # 检查选择了多少项
    selection = result_listbox.selection()
    item_count = len(selection)

    # 如果选择了多项，禁用“打开文件位置”
    if item_count > 1:
        menu.entryconfig("打开文件位置", state="disabled")
    else:
        menu.entryconfig("打开文件位置", state="normal")

    # 弹出菜单
    menu.post(event.x_root, event.y_root)


# 创建 GUI 窗口
root = tk.Tk()
root.geometry("600x600")  # 增大窗口尺寸以容纳更多控件
root.title("文件搜索器")
root.iconbitmap(r"C:\Windows\SystemApps\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\WindowsBackup\Assets\folderdocuments.ico")


# 使用队列进行线程间通信
found_files_queue = queue.Queue()
search_in_progress = False
# 用于跟踪复选框的状态
show_full_path = tk.BooleanVar(value=False)

# 创建一个容器来包含所有组件
mainframe = ttk.Frame(root, padding="20")
mainframe.grid(row=0, column=0, sticky="nsew")

# 目录输入框
directory_label = ttk.Label(mainframe, text="    搜索目录", justify='center')
directory_label.grid(row=0, column=0, sticky="w")
directory_entry = ttk.Entry(mainframe)
directory_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
directory_entry.insert(0, "D:\\")  # 设置默认搜索路径为 D:\
browse_button = ttk.Button(mainframe, text="浏览", command=browse_directory)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# 关键词输入框
keyword_label = ttk.Label(mainframe, text="关键词\n（支持通配符）", justify='center')
keyword_label.grid(row=1, column=0, sticky="w")
keyword_entry = ttk.Entry(mainframe, foreground="#000000")
keyword_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
keyword_entry.bind("<Return>", lambda event: start_search())  # 绑定 Enter 键触发搜索

# 搜索按钮
search_button = ttk.Button(mainframe, text="搜索", command=start_search)
search_button.grid(row=1, column=2, padx=5, pady=5)

# 停止搜索按钮
stop_button = ttk.Button(mainframe, text="停止搜索", command=stop_search)
stop_button.grid(row=1, column=3, padx=5, pady=5)

# 结果列表框
result_label = ttk.Label(mainframe, text="搜索结果（支持多选）：")
result_label.grid(row=2, column=0, columnspan=3, pady=5, sticky="w")
result_listbox = ttk.Treeview(mainframe, columns=("full_path"), selectmode="extended", show="tree") # 结果列表框，selectmode为'extended'以支持多选
result_listbox.heading("#0", text="文件名")
result_listbox.heading("full_path", text="完整路径")
result_listbox.column("full_path", stretch=0, width=0)
result_listbox.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

# 右键菜单
menu = tk.Menu(result_listbox, tearoff=0)
menu.add_command(label="打开文件", command=open_file)
menu.add_command(label="复制文件路径", command=copy_file_path)
menu.add_command(label="打开文件位置", command=open_location)
menu.add_command(label="删除到回收站", command=delete_files)
menu.add_separator()
menu.add_command(label="复制到新位置", command=copy_to_new_location)
result_listbox.bind("<Button-3>", popup_menu)

# 滚动条
scrollbar = ttk.Scrollbar(mainframe, orient=tk.VERTICAL, command=result_listbox.yview)
scrollbar.grid(row=3, column=3, sticky="ns")
result_listbox.config(yscrollcommand=scrollbar.set)

# 在主窗口底部添加状态栏
status_var = tk.StringVar()
status_bar = ttk.Label(root, textvariable=status_var, relief=tk.FLAT, style="Status.TLabel", padding=(10, 0, 0, 0))  # 左侧内边距为10
status_bar.grid(row=1, column=0, sticky="ew")

# 复选框控件
show_full_path_checkbox = ttk.Checkbutton(mainframe, text="显示完整路径", variable=show_full_path, command=toggle_display_mode)
show_full_path_checkbox.grid(row=2, column=2, sticky="w")


# 配置窗口自适应大小
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
mainframe.columnconfigure(1, weight=1)
mainframe.rowconfigure(3, weight=1)
mainframe.grid_rowconfigure(1, weight=0)

# 启动 GUI
root.mainloop()