function batch_process_folders()
    clear; close all;
    data_path = '/path/to/Datasets';
    % Expected data structure:
    % data_path (defined above)
    %    \_ 10mGy_FBP_80keV_R1
    %        \_ dicom files (actual names are not important)
    %    \_ 10mGy_FBP_80keV_R2
    %    \_ ...

    numerrors = 0;
    failed_files = {};
    failed_messages = {};
    reco_dirs = getSubfolders(data_path);

    imq_handle = imquest; % open up instance of imquest and save handle

    reco_ref = '10mGy_FBP_80keV_R1'; % a dataset where all insert are clearly visible

    % first analysis using a good scan to find the insert positions
    disp('=== Processing a clear dataset to find insert position...')
    params = processFolder(imq_handle, [data_path filesep reco_ref]);

    for i=1:length(reco_dirs) % loop over reconstruction folders
        reco_path = [data_path filesep reco_dirs(i).name];
        disp(['=== Reconstruction ' num2str(i) '/' num2str(length(reco_dirs)) ' : ' reco_path])
        if strcmp(reco_dirs(i).name, reco_ref)
            disp('    Already processed as reference dataset.')
            continue;
        end
        try
            processFolder(imq_handle, reco_path, params);
        catch ME
            numerrors = numerrors + 1;
            failed_files{numerrors} = reco_path;
            failed_messages{numerrors} = ME.message;
        end
    end
    
    fprintf('Number of failed files: %d\n', numerrors)
    for i=1:length(failed_files)
        disp(['    ' failed_files{i} ' (' failed_messages{i} ')'])
    end

end

function dirs = getSubfolders(path)
    items = dir([path filesep '*']);
    names = {items.name};
    flags = [items.isdir] & ~strcmp(names, '.') & ~strcmp(names, '..');
    dirs = items(flags);
end

function res = processFolder(imq_handle, case_path, params)
    disp(['    Processing ' case_path '...'])

    if nargin < 2
        error('Insufficient parameters')
    end

    json_save_path = [strrep(case_path, 'Datasets', 'PlotData') '.json'];

    if nargin == 3 && isfile(json_save_path)
        res = params;
        return;
    end
    
	T_landmark = 550;

    imq_handle.loadCTdata(case_path);

    if nargin < 3
        % external parameters not provided -> we calculate everything
        res = imquest_MercuryPhantomAutoAnalyze(imq_handle,'4.0');
    else
        % 'params' is defined
        res  = imquest_MercuryPhantomAutoAnalyze(imq_handle,'Bare');
        sliceSize = zeros(size(res.z));
        NPSslice = false(size(res.z));
        TTFslice = false(size(res.z));
        for j=1:length(params.PhantomDiameters)
            %Find the slice locations for this diameter
            ind = params.PhantomDiameters(j) == params.sliceSize;
            zmin = min(params.z(ind));
            zmax = max(params.z(ind));
            ind2 = res.z >= zmin & res.z <= zmax;
            sliceSize(ind2) = params.PhantomDiameters(j);
            %Find the NPS slice locations for this diameter
            zmin = min(params.z(ind & params.NPSslice));
            zmax = max(params.z(ind & params.NPSslice));
            ind2 = res.z >= zmin & res.z <= zmax;
            NPSslice(ind2) = true;
            %Find the TTF slice locations for this diameter
            zmin = min(params.z(ind & params.TTFslice));
            zmax = max(params.z(ind & params.TTFslice));
            ind2 = res.z >= zmin & res.z <= zmax;
            TTFslice(ind2) = true;
        end
        diameter = interp1(params.z,params.diameter,res.z);
        res.phantomVersion = '4.0';
        res.sliceSize = sliceSize;
        res.NPSslice = NPSslice;
        res.TTFslice = TTFslice;
        res.diameter = diameter;
        res.T_landmark = T_landmark;
        [res.TTFs, res.NPSs, res.Dprimes] = makeDprimeMeasurements(res);
        [res.fits, res.gofs] = makeDprimevsSizeFits(res);
    end

    save_json_results(json_save_path, res);

end
